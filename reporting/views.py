import base64
import io
import json
import os
import textwrap
import uuid
import zipfile
from collections import Counter, OrderedDict, defaultdict
from io import BytesIO
from statistics import mean
from typing import List
from urllib.parse import quote as urlquote

import plotly.colors as pc
import plotly.graph_objects as go
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Avg, Count, F, Min, OuterRef, Subquery
from django.db.models.functions import Floor
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import activate, deactivate_all
from django.utils.translation import gettext_lazy as _
from django_otp.decorators import otp_required
from weasyprint import CSS, HTML

from governanceplatform.helpers import get_sectors_grouped, user_in_group
from governanceplatform.models import Company, Sector
from securityobjectives.models import (
    Domain,
    MaturityLevel,
    SecurityObjective,
    SecurityObjectiveStatus,
    StandardAnswer,
)

from .filters import CompanyFilter, RecommendationFilter
from .forms import (
    CompanySelectFormSet,
    ConfigurationReportForm,
    ImportRiskAnalysisForm,
    RecommendationsSelectFormSet,
)
from .models import (
    AssetData,
    CompanyReporting,
    Observation,
    ObservationRecommendation,
    RecommendationData,
    RiskData,
    SectorReportConfiguration,
    ServiceStat,
    ThreatData,
    VulnerabilityData,
)

# GLOBALS
SECTOR_LEGEND = _("Sector average")
SO_COLOR_PALETTE = [
    (0, "#F8696B"),
    (0.5, "#FA9473"),
    (1, "#FCBF7B"),
    (1.5, "#FFEB84"),
    (2, "#CCDD82"),
    (2.5, "#98CE7F"),
    (3, "#63BE7B"),
]


@login_required
@otp_required
def reporting(request):
    user = request.user

    companies_queryset = (
        Company.objects.filter(
            companyuser__sectors__in=user.get_sectors().values_list("id", flat=True)
        ).distinct()
        if user_in_group(user, "RegulatorUser")
        else Company.objects.all()
    )

    if "reset" in request.GET:
        request.session.pop("reporting_filter_params", None)
        return redirect("reporting")

    current_params = request.session.get("reporting_filter_params", {}).copy()

    for key, values in request.GET.lists():
        current_params[key] = values if key == "sectors" else values[0]

    reporting_filter_params = current_params
    request.session["reporting_filter_params"] = current_params

    year = int(reporting_filter_params.get("year") or timezone.now().year)

    sectors_filters = reporting_filter_params.get("sectors", [])

    company_filter = CompanyFilter(reporting_filter_params, queryset=companies_queryset)

    is_filtered = {k: v for k, v in reporting_filter_params.items()}

    if request.method == "POST":
        formset = CompanySelectFormSet(
            request.POST,
            queryset=company_filter.qs,
            year=year,
            sectors_filter=sectors_filters,
        )
        if formset.is_valid():
            selected_companies = [
                {
                    "company": form.cleaned_data.get("id"),
                    "sector": form.cleaned_data.get("sector"),
                }
                for form in formset
                if form.cleaned_data.get("selected")
            ]
            is_multiple_selected_companies = len(selected_companies) > 1
            zip_buffer = io.BytesIO()
            error_messages = []
            errors = 0
            with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                for select_company in selected_companies:
                    company = select_company.get("company")
                    sector = select_company.get("sector")
                    try:
                        company_reporting = CompanyReporting.objects.get(
                            company=company, year=year, sector=sector
                        )
                    except CompanyReporting.DoesNotExist:
                        if is_multiple_selected_companies:
                            error_message = f"No reporting data found in sector: {str(sector)} and year: {year}"
                            error_messages.append(error_message)
                            continue
                        else:
                            messages.error(
                                request,
                                _("No reporting data"),
                            )
                            return redirect("reporting")
                    try:
                        sector_configuration = SectorReportConfiguration.objects.get(
                            sector=sector
                        )
                        nb_years = sector_configuration.number_of_year
                        threshold_for_high_risk = (
                            sector_configuration.threshold_for_high_risk
                        )
                        top_ranking = sector_configuration.top_ranking
                        so_excluded = sector_configuration.so_excluded.all()
                    except SectorReportConfiguration.DoesNotExist:
                        if is_multiple_selected_companies:
                            error_message = f"No data found in sector: {str(sector)} and year: {year}"
                            error_messages.append(error_message)
                            continue
                        else:
                            messages.error(
                                request,
                                _("No configuration for sector"),
                            )
                            return redirect("reporting")

                    security_objectives_declaration = StandardAnswer.objects.filter(
                        submitter_company=company,
                        sectors=sector,
                        year_of_submission=year,
                        status="PASS",
                    ).order_by("submit_date")

                    risk_analysis_stats = company.risk_analysis_exists(year, sector)

                    if not security_objectives_declaration:
                        if is_multiple_selected_companies:
                            error_message = f"{company}: No security objective data found in sector: {str(sector)} and year: {year}"
                            error_messages.append(error_message)
                            continue
                        else:
                            errors += 1
                            messages.error(
                                request,
                                _("No data found for security objectives report"),
                            )

                    if not risk_analysis_stats:
                        if is_multiple_selected_companies:
                            error_message = f"{company}: No risk data found in sector: {str(sector)} and year: {year}"
                            error_messages.append(error_message)
                            continue
                        else:
                            errors += 1
                            messages.error(
                                request,
                                _("No data found for risk report"),
                            )

                    if errors > 0:
                        return redirect("reporting")

                    report_recommendations = company.get_report_recommandations(
                        year, sector
                    )

                    report_data = {
                        "company": company,
                        "sector": sector,
                        "year": year,
                        "threshold_for_high_risk": threshold_for_high_risk,
                        "top_ranking": top_ranking,
                        "nb_years": nb_years,
                        "so_excluded": so_excluded,
                        "report_recommendations": report_recommendations,
                        "company_reporting": company_reporting,
                    }

                    pdf_report = get_pdf_report(request, report_data)
                    sector_name = sector.get_safe_translation()
                    filename = urlquote(
                        f"{_('annual_report')}_{year}_{company.name}_{sector_name}.pdf"
                    )
                    zip_file.writestr(filename, pdf_report.read())

                if error_messages:
                    error_log = "\n".join(error_messages)
                    zip_file.writestr("error_log.txt", error_log)

            zip_buffer.seek(0)

            if is_multiple_selected_companies:
                response = HttpResponse(zip_buffer, content_type="application/zip")
                response["Content-Disposition"] = 'attachment; filename="reports.zip"'
            else:
                pdf_report.seek(0)
                response = HttpResponse(pdf_report, content_type="application/pdf")
                response["Content-Disposition"] = f'attachment; filename="{filename}"'

            return response

    formset = CompanySelectFormSet(
        queryset=company_filter.qs, year=year, sectors_filter=sectors_filters
    )

    context = {
        "formset": formset,
        "filter": company_filter,
        "is_filtered": bool(is_filtered),
    }

    return render(request, "reporting/dashboard.html", context)


@login_required
@otp_required
def report_configuration(request):
    user = request.user
    report_configuration_queryset = (
        SectorReportConfiguration.objects.filter(
            sector__in=user.get_sectors().values_list("id", flat=True)
        ).distinct()
        if user_in_group(user, "RegulatorUser")
        else SectorReportConfiguration.objects.all()
    )

    context = {"report_configurations": report_configuration_queryset}
    return render(request, "reporting/report_configuration.html", context=context)


@login_required
@otp_required
def add_report_configuration(request):
    user = request.user
    user_sectors = (
        user.get_sectors().all()
        if user_in_group(user, "RegulatorUser")
        else Sector.objects.annotate(child_count=Count("children")).exclude(
            parent=None, child_count__gt=0
        )
    )

    report_configuration_queryset = (
        SectorReportConfiguration.objects.filter(
            sector__in=user_sectors.values_list("id", flat=True)
        ).distinct()
        if user_in_group(user, "RegulatorUser")
        else SectorReportConfiguration.objects.all()
    )

    sectors_queryset = (
        user_sectors
        if user_in_group(user, "RegulatorUser")
        else Sector.objects.annotate(child_count=Count("children")).exclude(
            parent=None, child_count__gt=0
        )
    )

    initial_sectors_queryset = sectors_queryset.exclude(
        id__in=report_configuration_queryset.values_list("sector__id", flat=True)
    )
    if not initial_sectors_queryset:
        messages.error(
            request,
            _("All sectors have been configured"),
        )
        return redirect("report_configuration")

    initial = {"sectors": initial_sectors_queryset}
    if request.method == "POST":
        form = ConfigurationReportForm(request.POST, initial=initial)
        if form.is_valid():
            cleaned_data = form.cleaned_data.copy()
            so_excluded = cleaned_data.pop("so_excluded", None)
            new_configuration = SectorReportConfiguration(**cleaned_data)
            new_configuration.save()
            if so_excluded:
                new_configuration.so_excluded.set(so_excluded)
            return redirect("report_configuration")

    form = ConfigurationReportForm(initial=initial)
    context = {"form": form}
    return render(request, "reporting/add_report_configuration.html", context=context)


@login_required
@otp_required
def edit_report_configuration(request, report_configuration_id: int):
    user = request.user

    try:
        report_configuration = SectorReportConfiguration.objects.get(
            pk=report_configuration_id
        )
    except SectorReportConfiguration.DoesNotExist:
        messages.error(request, _("Configuration not found"))
        return redirect("report_configuration")

    user_sectors = (
        user.get_sectors().all()
        if user_in_group(user, "RegulatorUser")
        else Sector.objects.all()
    )

    if report_configuration.sector not in user_sectors:
        messages.error(request, _("Forbidden"))
        return redirect("report_configuration")

    if request.method == "POST":
        form = ConfigurationReportForm(request.POST, instance=report_configuration)
        if form.is_valid():
            form.save()
            return redirect("report_configuration")

    form = ConfigurationReportForm(instance=report_configuration)
    context = {"form": form}
    return render(request, "reporting/add_report_configuration.html", context=context)


@login_required
@otp_required
def report_recommendations(request, company_id, sector_id, year):
    validate_result = validate_url_arguments(request, company_id, sector_id, year)
    if isinstance(validate_result, HttpResponseRedirect):
        return validate_result
    company, sector, year = validate_result
    report_recommendations = company.get_report_recommandations(year, sector)

    context = {
        "recommendations": report_recommendations,
        "company": company,
        "sector": sector,
        "year": year,
    }

    return render(request, "reporting/recommendations.html", context=context)


@login_required
@otp_required
def add_report_recommendations(request, company_id, sector_id, year):
    validate_result = validate_url_arguments(request, company_id, sector_id, year)
    if isinstance(validate_result, HttpResponseRedirect):
        return validate_result
    company, sector, year = validate_result

    redirect_url = reverse(
        "add_report_recommendations", args=[company.id, sector.id, year]
    )

    if "reset" in request.GET:
        request.session.pop("report_recommendations_filter_params", None)
        return redirect(redirect_url)

    current_params = request.session.get(
        "report_recommendations_filter_params", {}
    ).copy()

    for key, values in request.GET.lists():
        current_params[key] = values if key == "sectors" else values[0]

    filter_params = current_params
    request.session["report_recommendations_filter_params"] = current_params

    report_recommendations = company.get_report_recommandations(year, sector)
    recommendations_ids = [rec.id for rec in report_recommendations]

    recommendations_queryset = ObservationRecommendation.objects.exclude(
        id__in=recommendations_ids
    )

    recommendation_filter = RecommendationFilter(
        filter_params, queryset=recommendations_queryset
    )

    is_filtered = {k: v for k, v in filter_params.items()}

    if request.method == "POST":
        formset = RecommendationsSelectFormSet(request.POST)
        if formset.is_valid():
            selected_recommendations = [
                form.instance for form in formset if form.cleaned_data.get("selected")
            ]

            add_new_report_recommendations(
                company, sector, year, selected_recommendations
            )
            messages.success(
                request,
                _("Recommendations have been added successfully"),
            )
            redirect_url = reverse(
                "report_recommendations", args=[company.id, sector.id, year]
            )

            return redirect(redirect_url)

    formset = RecommendationsSelectFormSet(queryset=recommendation_filter.qs)

    context = {
        "formset": formset,
        "filter": recommendation_filter,
        "is_filtered": bool(is_filtered),
        "company": company,
        "sector": sector,
        "year": year,
    }

    return render(request, "reporting/add_recommendations.html", context=context)


@login_required
@otp_required
def copy_report_recommendations(request, company_id, sector_id, year):
    validate_result = validate_url_arguments(request, company_id, sector_id, year)
    if isinstance(validate_result, HttpResponseRedirect):
        return validate_result
    company, sector, year = validate_result
    last_year = year - 1
    report_recommendations = company.get_report_recommandations(last_year, sector)
    if not report_recommendations:
        messages.error(
            request,
            _(f"No recommendations from { last_year }"),
        )
    else:
        add_new_report_recommendations(company, sector, year, report_recommendations)
        messages.success(
            request,
            _(f"Recommendations have been copied from { last_year }"),
        )

    redirect_url = reverse("report_recommendations", args=[company_id, sector_id, year])
    return redirect(redirect_url)


@login_required
@otp_required
def delete_report_recommendation(request, company_id, sector_id, year, report_rec_id):
    validate_result = validate_url_arguments(request, company_id, sector_id, year)
    if isinstance(validate_result, HttpResponseRedirect):
        return validate_result
    company, sector, year = validate_result

    try:
        company_reporting = CompanyReporting.objects.get(
            company=company, year=year, sector=sector
        )
        observation = Observation.objects.get(
            company_reporting=company_reporting,
            observation_recommendations__in=[report_rec_id],
        )

        recommendation = ObservationRecommendation.objects.get(id=report_rec_id)

    except (
        Observation.DoesNotExist,
        CompanyReporting.DoesNotExist,
        ObservationRecommendation.DoesNotExist,
    ):
        messages.error(request, _("No report recommendation found"))
        return redirect("reporting")

    observation.observation_recommendations.remove(recommendation)
    messages.success(request, _("The report recommendation has been deleted."))
    redirect_url = reverse("report_recommendations", args=[company.id, sector.id, year])

    return redirect(redirect_url)


@login_required
@otp_required
def import_risk_analysis(request):
    user = request.user
    sectors_queryset = (
        user.get_sectors().all()
        if user_in_group(user, "RegulatorUser")
        else Sector.objects.all()
    )

    sector_list = get_sectors_grouped(sectors_queryset)

    companies_queryset = (
        Company.objects.filter(
            companyuser__sectors__in=user.get_sectors().values_list("id", flat=True)
        ).distinct()
        if user_in_group(user, "RegulatorUser")
        else Company.objects.all()
    )

    company_list = [(company.id, str(company)) for company in companies_queryset]

    initial = {
        "company": company_list,
        "sectors": sector_list,
    }

    if request.method == "POST":
        form = ImportRiskAnalysisForm(request.POST, request.FILES, initial=initial)
        if form.is_valid():
            json_file = form.cleaned_data["import_file"]
            company_id = form.cleaned_data["company"]
            sector_ids = form.cleaned_data["sectors"]
            year = form.cleaned_data["year"]
            try:
                validate_json_file(json_file)
            except ValidationError as e:
                messages.error(request, f"Error: {str(e)}")
                return redirect("import_risk_analysis")

            for sector_id in sector_ids:
                validate_result = validate_url_arguments(
                    request, company_id, sector_id, year
                )
                if isinstance(validate_result, HttpResponseRedirect):
                    return redirect("import_risk_analysis")

                company, sector, year = validate_result
                company_sectors = company.get_queryset_sectors()
                if sector not in company_sectors:
                    messages.error(
                        request,
                        f"Sector error: {str(sector)} is not linked to the {str(company)}",
                    )
                    continue

                company_reporting_obj, created = CompanyReporting.objects.get_or_create(
                    company=company, year=year, sector=sector
                )

                try:
                    parsing_risk_data_json(
                        json_file, company_reporting_obj, not created
                    )
                except Exception as e:
                    messages.error(request, f"Parsing error: {str(e)}")
                    return redirect("import_risk_analysis")

                messages.success(request, _("Risk analysis successfully imported"))

    form = ImportRiskAnalysisForm(initial=initial)
    context = {"form": form}
    return render(request, "reporting/risk_analysis_import.html", context=context)


def get_so_data(cleaned_data):
    def get_latest_answers(company, sector, year):
        latest_submit_date = (
            StandardAnswer.objects.filter(
                submitter_company=OuterRef("submitter_company"),
                sectors=sector,
                year_of_submission=year,
                status="PASS",
            )
            .order_by("-submit_date")
            .values("submit_date")[:1]
        )

        queryset = StandardAnswer.objects.filter(
            sectors=sector,
            year_of_submission=year,
            status="PASS",
            submit_date=Subquery(latest_submit_date),
        ).distinct()

        if company is not None:
            queryset = queryset.filter(submitter_company=company)

        return queryset

    def calculate_evolution(previous_data, current_score):
        if previous_data:
            previous_score = previous_data["score"]
            if previous_score > current_score:
                return False
            elif previous_score < current_score:
                return True
        return None

    def build_dict_scores(queryset, target_dict, key_func, year, sector_values=False):
        for item in queryset:
            key = key_func(item)
            score_field = "score_value"

            if isinstance(item, dict):
                score = item[score_field]
            else:
                score = getattr(item, score_field)

            if sector_values:
                target_dict[key][year]["sector_avg"] = score
            else:
                previous_year = year - 1
                previous_data = target_dict[key].get(previous_year)
                evolution = calculate_evolution(previous_data, score)
                target_dict[key][year] = {
                    "score": score,
                    "evolution": evolution,
                }

    def build_radar_data(data_dict, sector_avg_field=None):
        radar_data = defaultdict()
        score_field = "score"
        for __key, years in data_dict.items():
            for year, values in years.items():
                year_label = f"{company} {year}"
                radar_data.setdefault(year_label, []).append(values[score_field])

                if sector_avg_field and year == current_year:
                    radar_data.setdefault(f"{SECTOR_LEGEND} {current_year}", []).append(
                        values[sector_avg_field]
                    )

        return dict(radar_data)

    def build_bar_chart_by_level_data(counts, label):
        levels_count = maturity_levels_queryset.count()
        score_list = [counts.get(level, 0) for level in range(levels_count)]
        bar_chart_data_by_level[label] = score_list

    company = cleaned_data["company"]
    sector = cleaned_data["sector"]
    current_year = cleaned_data["year"]
    nb_years = cleaned_data["nb_years"]
    so_excluded = cleaned_data["so_excluded"]
    maturity_levels_queryset = MaturityLevel.objects.order_by("level")
    maturity_levels = [str(level) for level in maturity_levels_queryset]
    years_list = []
    sector_so_by_year_desc = OrderedDict()
    sector_so_by_year_asc = OrderedDict()
    bar_chart_data_by_level = defaultdict()
    company_so_by_year = defaultdict(lambda: {})
    company_so_by_domain = defaultdict(lambda: {})
    company_so_by_priority = defaultdict(lambda: {})
    radar_chart_data_by_domain = defaultdict()
    radar_chart_data_by_year = defaultdict()
    so_data = defaultdict()

    for offset in range(nb_years):
        year = current_year - nb_years + offset + 1
        company_so_by_level = defaultdict(list)
        latest_answers = get_latest_answers(company, sector, year)

        if latest_answers.exists():
            years_list.append(year)

        # Company Querysets
        # TO DO : manage the case when it's empty
        floored_company_queryset = (
            SecurityObjectiveStatus.objects.filter(standard_answer__in=latest_answers)
            .exclude(security_objective__in=so_excluded)
            .annotate(score_value=Floor(F("score")))
        )

        so_domain_company_queryset = (
            floored_company_queryset.values("security_objective__domain")
            .annotate(score_value=Avg("score"))
            .order_by("security_objective__domain")
        )

        sorted_company_queryset = floored_company_queryset.annotate(
            min_position=Min(
                "security_objective__securityobjectivesinstandard__position"
            )
        )

        company_by_priority_queryset = floored_company_queryset.annotate(
            min_priority=Min(
                "security_objective__securityobjectivesinstandard__priority"
            )
        ).order_by("score_value", "min_priority")

        aggregated_scores_queryset = floored_company_queryset.values(
            "score_value"
        ).annotate(count=Count("score_value"))

        # Sector Querysets

        latest_answers_sector = get_latest_answers(None, sector, year)

        sector_queryset = SecurityObjectiveStatus.objects.filter(
            standard_answer__in=latest_answers_sector
        ).exclude(security_objective__in=so_excluded)

        sector_score_by_domain_queryset = (
            sector_queryset.values("security_objective__domain")
            .annotate(score_value=Avg("score"))
            .order_by("security_objective__domain")
        )

        sector_scores_queryset = sector_queryset.values("security_objective").annotate(
            score_value=Floor(Avg("score"))
        )

        # Dictionaries

        # by_level
        for score_data in sorted_company_queryset.order_by(
            "score_value", "min_position"
        ):
            level = maturity_levels_queryset.filter(
                level=int(score_data.score_value)
            ).first()
            security_objective = score_data.security_objective
            company_so_by_level[str(level)].append(security_objective)

        # by_domain
        build_dict_scores(
            so_domain_company_queryset,
            company_so_by_domain,
            lambda x: Domain.objects.get(pk=x["security_objective__domain"]),
            year,
        )

        # by_domain [sector]
        build_dict_scores(
            sector_score_by_domain_queryset,
            company_so_by_domain,
            lambda x: Domain.objects.get(pk=x["security_objective__domain"]),
            year,
            True,
        )

        # by_year
        build_dict_scores(
            sorted_company_queryset.order_by("min_position"),
            company_so_by_year,
            lambda x: x.security_objective,
            year,
        )

        # by_priority
        build_dict_scores(
            company_by_priority_queryset,
            company_so_by_priority,
            lambda x: x.security_objective,
            year,
        )

        # Bar chart by level
        company_counts = Counter(
            {
                score_data["score_value"]: score_data["count"]
                for score_data in aggregated_scores_queryset
            }
        )

        sector_counts = Counter(
            {
                score_data["score_value"]: sector_scores_queryset.filter(
                    score_value=score_data["score_value"]
                ).count()
                for score_data in sector_scores_queryset
            }
        )

        build_bar_chart_by_level_data(
            counts=company_counts,
            label=f"{company} {year}",
        )

        build_bar_chart_by_level_data(
            counts=sector_counts,
            label=f"{SECTOR_LEGEND} {year}",
        )

        # Sector asc and desc lists by score

        sector_so_by_year_asc[year] = [
            SecurityObjective.objects.get(pk=score["security_objective"])
            for score in sector_scores_queryset.order_by("score_value")
        ]

        sector_so_by_year_desc[year] = list(sector_so_by_year_asc[year])
        sector_so_by_year_desc[year].reverse()

    radar_chart_data_by_domain = build_radar_data(company_so_by_domain, "sector_avg")
    radar_chart_data_by_year = build_radar_data(company_so_by_year)

    so_data = {
        "years": years_list,
        "domains": [str(domain) for domain in company_so_by_domain.keys()],
        "maturity_levels": maturity_levels,
        "unique_codes_list": [so.unique_code for so in company_so_by_year.keys()],
        "max_of_company_count": max(company_counts.values()),
        "bar_chart_data_by_level": dict(sort_legends(bar_chart_data_by_level)),
        "company_so_by_level": dict(company_so_by_level),
        "company_so_by_domain": dict(company_so_by_domain),
        "company_so_by_year": dict(company_so_by_year),
        "company_so_by_priority": dict(company_so_by_priority),
        "sector_so_by_year_desc": dict(sector_so_by_year_desc),
        "sector_so_by_year_asc": dict(sector_so_by_year_asc),
        "radar_chart_data_by_domain": radar_chart_data_by_domain,
        "radar_chart_data_by_year": radar_chart_data_by_year,
    }

    return so_data


def get_risk_data(cleaned_data):
    def build_risk_average_data(service):
        service_stat_queryset = ServiceStat.objects.filter(
            service=service,
            company_reporting__year=year,
            company_reporting__sector=sector,
        )

        average_risks_by_sector = service_stat_queryset.aggregate(
            avg_current_risks=Avg("avg_current_risks")
        )["avg_current_risks"]

        servicestat_by_company = service_stat_queryset.filter(
            company_reporting__company=company,
        )

        average_risks_by_company = (
            servicestat_by_company.first().avg_current_risks
            if servicestat_by_company
            else 0
        )

        for label in labels:
            data_by_risk_average.setdefault(label, [])

        data_by_risk_average[company_label].append(
            round_value(average_risks_by_company)
        )

        data_by_risk_average[sector_label].append(round_value(average_risks_by_sector))

    def build_high_risk_data(service):
        # Querysets
        risk_data_service_queryset = RiskData.objects.filter(
            service__service=service,
            service__company_reporting__year=year,
            service__company_reporting__sector=sector,
            max_risk__gt=threshold_for_high_risk,
        ).exclude(risk_treatment="UNTRE")

        service_stat_queryset = ServiceStat.objects.filter(
            service=service,
            company_reporting__year=year,
            company_reporting__company=company,
            company_reporting__sector=sector,
        )

        high_risks_by_company = risk_data_service_queryset.filter(
            service__company_reporting__company=company,
        ).aggregate(count=Count("id"), max_risk_avg=Avg("max_risk"))

        high_risks_average_by_sector = risk_data_service_queryset.aggregate(
            max_risk_avg=Avg("max_risk")
        )

        # High risk rate data
        total_high_risks = high_risks_by_company["count"]

        total_risk = (
            service_stat_queryset.first().total_treated_risks
            if service_stat_queryset
            else 0
        )

        rate = (total_high_risks / total_risk) if total_risk else 0

        data_by_high_risk_rate.setdefault(year, {"rate_labels": [], "rate_values": []})

        data_by_high_risk_rate[year]["rate_labels"].append(
            f"{total_high_risks} / {int(total_risk)}"
        )
        data_by_high_risk_rate[year]["rate_values"].append(rate)

        # High risk average data
        for label in labels:
            data_by_high_risk_average.setdefault(label, [])

        data_by_high_risk_average[company_label].append(
            round_value(high_risks_by_company["max_risk_avg"])
        )
        data_by_high_risk_average[sector_label].append(
            round_value(high_risks_average_by_sector["max_risk_avg"])
        )

    def build_evolution_highest_risks_data(company_reporting):
        risks_data = (
            RiskData.objects.filter(
                service__company_reporting=company_reporting,
            )
            .exclude(risk_treatment="UNTRE")
            .annotate(total_impact=F("impact_c") + F("impact_i") + F("impact_a"))
            .order_by(
                "-max_risk",
                "-total_impact",
                "-threat_value",
                "-vulnerability_value",
                "asset__translations__name",
            )
        )

        data_evolution_highest_risks[current_year] = [
            round_value(max_risk)
            for max_risk in risks_data[:top_ranking].values_list("max_risk", flat=True)
        ]
        i = nb_years
        past_year = current_year
        while i > 1:
            i -= 1
            past_year -= 1
            data_evolution_highest_risks[past_year] = []
            for risk in risks_data[:top_ranking]:
                try:
                    risk = RiskData.objects.get(
                        uuid=risk.uuid,
                        service__company_reporting__year=past_year,
                        service__company_reporting__company=company,
                        service__company_reporting__sector=sector,
                    )
                    max_risk = risk.max_risk
                except RiskData.DoesNotExist:
                    risk = RiskData.objects.none()
                    max_risk = 0

                data_evolution_highest_risks[past_year].append(round_value(max_risk))

    company = cleaned_data["company"]
    sector = cleaned_data["sector"]
    current_year = cleaned_data["year"]
    nb_years = cleaned_data["nb_years"]
    threshold_for_high_risk = cleaned_data["threshold_for_high_risk"]
    top_ranking = cleaned_data["top_ranking"]
    company_reporting = cleaned_data["company_reporting"]
    data_by_risk_average = defaultdict()
    data_by_high_risk_rate = defaultdict()
    data_by_high_risk_average = defaultdict()
    data_evolution_highest_risks = defaultdict(lambda: {})
    services_list = AssetData.objects.filter(
        servicestat__company_reporting=company_reporting
    ).order_by("id")
    operator_services = list(services_list.values_list("translations__name", flat=True))
    operator_services_with_all = [_("All services")] + operator_services

    for offset in range(nb_years):
        year = current_year - nb_years + offset + 1
        company_label = f"{company} {year}"
        sector_label = f"{SECTOR_LEGEND} {year}"
        labels = [company_label, sector_label]

        for service in services_list:
            build_risk_average_data(service)
            build_high_risk_data(service)

        # Score mean for all services
        for label in labels:
            data_by_risk_average[label].insert(
                0, round_value(mean(data_by_risk_average[label]))
            )
            data_by_high_risk_average[label].insert(
                0, round_value(mean(data_by_high_risk_average[label]))
            )
        if year == current_year:
            build_evolution_highest_risks_data(company_reporting)

    risk_data = {
        "data_by_risk_average": dict(sort_legends(data_by_risk_average)),
        "data_by_high_risk_rate": dict(data_by_high_risk_rate),
        "data_by_high_risk_average": dict(sort_legends(data_by_high_risk_average)),
        "data_evolution_highest_risks": dict(
            sort_legends(data_evolution_highest_risks)
        ),
        "operator_services": operator_services,
        "operator_services_with_all": operator_services_with_all,
    }

    return risk_data


def generate_bar_chart(data, labels, is_rate=False):
    fig = go.Figure()
    labels = text_wrap(labels)
    bar_colors_palette = pc.qualitative.Pastel1
    average_colors_palette = pc.qualitative.Set1
    avg_index = 0
    bar_index = 0

    for name, values in data.items():
        if is_rate:
            rate_labels = values["rate_labels"]
            values = values["rate_values"]

        group_name = str(name)[-4:]

        if str(_("average")) in str(name):
            fig.add_trace(
                go.Scatter(
                    x=labels,
                    y=values,
                    name=name,
                    mode="markers",
                    marker=dict(
                        size=12,
                        symbol="diamond",
                        color=average_colors_palette[avg_index],
                    ),
                    offsetgroup=group_name,
                    legendgroup=group_name,
                ),
            )
            avg_index += 1

        else:
            fig.add_trace(
                go.Bar(
                    x=labels,
                    y=values,
                    name=name,
                    marker_color=bar_colors_palette[bar_index],
                    text=rate_labels if is_rate else values,
                    textposition="outside",
                    offsetgroup=group_name,
                    legendgroup=group_name,
                ),
            )
            bar_index += 1

    fig.update_layout(
        hovermode="closest",
        barmode="group",
        scattermode="group",
        bargroupgap=0.2,
        xaxis=dict(
            linecolor="black",
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="lightgray",
            linecolor="black",
        ),
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=True,
        legend=dict(
            orientation="h",
            x=0.5,
            y=-0.2,
            xanchor="center",
            yanchor="top",
            traceorder="normal",
            itemwidth=70,
            valign="middle",
        ),
        margin=dict(l=0, r=0, t=0, b=50),
    )

    if is_rate:
        fig.update_layout(yaxis_tickformat=".0%")

    graph = convert_graph_to_base64(fig)

    return graph


def generate_radar_chart(data, labels, levels):
    fig = go.Figure()
    labels = text_wrap(labels)
    line_colors_palette = pc.qualitative.Pastel1
    marker_colors_palette = pc.qualitative.Set1
    index = 0

    for name, values in data.items():
        line_style = "solid"
        line_color = line_colors_palette[index]
        marker_color = marker_colors_palette[index]
        symbol = "circle"

        if str(_("average")) in name:
            line_style = "dash"
            line_color = "#666666"
            marker_color = "#222A2A"
            symbol = "triangle-up"

        fig.add_trace(
            go.Scatterpolar(
                r=values + [values[0]],
                theta=labels + [labels[0]],
                name=str(name),
                fillcolor="rgba(0,0,0,0)",
                marker=dict(
                    symbol=symbol,
                    color=marker_color,
                ),
                mode="lines+markers",
                line=dict(
                    color=line_color,
                    dash=line_style,
                ),
            )
        )
        index += 1

    fig.update_layout(
        polar=dict(
            bgcolor="white",
            gridshape="linear",
            radialaxis=dict(
                range=[0, len(levels) - 1],
                gridcolor="lightgrey",
                angle=90,
                tickangle=90,
            ),
            angularaxis=dict(
                gridcolor="lightgrey",
                tickmode="array",
                linecolor="lightgrey",
                rotation=90,
                direction="clockwise",
            ),
        ),
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=True,
        legend=dict(
            orientation="h",
            x=0.5,
            y=-0.1,
            xanchor="center",
            yanchor="top",
            traceorder="normal",
            itemwidth=70,
            valign="middle",
        ),
        margin=dict(l=0, r=0, t=50, b=0),
    )

    graph = convert_graph_to_base64(fig)

    return graph


def generate_colorbar():
    levels = [0, 0.5, 1, 1.5, 2, 2.5, 3]
    labels = [
        "no measure or N/A",
        "",
        "basic",
        "",
        "industry standard",
        "",
        "state of the art",
    ]

    fig = go.Figure(
        data=go.Scatter(
            x=[None],
            y=[None],
            mode="markers",
            marker=dict(
                size=0,
                color=[-0.1, 3],
                colorscale=[
                    [0.0, "#F8696B"],
                    [0.17, "#FA9473"],
                    [0.33, "#FCBF7B"],
                    [0.5, "#FFEB84"],
                    [0.67, "#CCDD82"],
                    [0.83, "#98CE7F"],
                    [1.0, "#63BE7B"],
                ],
                colorbar=dict(
                    outlinecolor="#FFFFFF",
                    outlinewidth=0.5,
                    tickvals=levels,
                    ticktext=labels,
                    orientation="h",
                    x=0.5,
                    y=0.5,
                    xanchor="center",
                    thickness=15,
                    ypad=0,
                ),
            ),
        )
    )

    annotations = [
        dict(
            x=0.02,
            y="no measure or N/A",
            text="0",
            showarrow=False,
            xref="paper",
            yref="paper",
            xanchor="center",
        ),
        dict(
            x=0.19,
            y="",
            text="0.5",
            showarrow=False,
            xref="paper",
            yref="paper",
            xanchor="center",
        ),
        dict(
            x=0.35,
            y="basic",
            text="1",
            showarrow=False,
            xref="paper",
            yref="paper",
            xanchor="center",
        ),
        dict(
            x=0.5,
            y="",
            text="1.5",
            showarrow=False,
            xref="paper",
            yref="paper",
            xanchor="center",
        ),
        dict(
            x=0.67,
            y="industry standard",
            text="2",
            showarrow=False,
            xref="paper",
            yref="paper",
            xanchor="center",
        ),
        dict(
            x=0.83,
            y="",
            text="2.5",
            showarrow=False,
            xref="paper",
            yref="paper",
            xanchor="center",
        ),
        dict(
            x=0.98,
            y="state of the art",
            text="3",
            showarrow=False,
            xref="paper",
            yref="paper",
            xanchor="center",
        ),
    ]

    fig.update_layout(annotations=annotations)

    fig.update_layout(
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False, range=[0, 1]),
        yaxis=dict(showticklabels=False, showgrid=False, zeroline=False, range=[0, 1]),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=40, t=200, b=15),
        height=50,
    )

    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)

    graph = convert_graph_to_base64(fig)

    return graph


def text_wrap(text, max_line_length=20):
    if isinstance(text, list):
        text_wrapped = [
            "<br>".join(textwrap.wrap(label, width=max_line_length)) for label in text
        ]
    elif isinstance(text, str):
        text_wrapped = "<br>".join(textwrap.wrap(text, width=max_line_length))
    else:
        return None
    return text_wrapped


def sort_legends(data):
    return sorted(
        data.items(),
        key=lambda x: (x[0] != SECTOR_LEGEND, x[0]),
    )


def round_value(value):
    if value is None:
        return 0

    if isinstance(value, int):
        return value

    rounded_value = round(value, 2)

    return (
        int(rounded_value)
        if rounded_value.is_integer()
        else float(f"{rounded_value:.2f}")
    )


def convert_graph_to_base64(fig):
    buffer = BytesIO()
    fig.write_image(buffer, format="png")
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()

    graph = base64.b64encode(image_png)
    graph = graph.decode("utf-8")

    return graph


def parsing_risk_data_json(json_file, company_reporting_obj, is_update=False):
    LANG_VALUES = {1: "fr", 2: "en", 3: "de", 4: "nl"}
    TREATMENT_VALUES = {
        1: "REDUC",
        2: "DENIE",
        3: "ACCEP",
        4: "SHARE",
        5: "UNTRE",
    }

    def create_translations(class_model, values, field_name):
        new_object, created = class_model.objects.get_or_create(uuid=values["uuid"])

        if created:
            for lang_index, lang_code in LANG_VALUES.items():
                name_value = values[field_name + str(lang_index)]
                if name_value:
                    activate(lang_code)
                    new_object.set_current_language(lang_code)
                    new_object.name = name_value

            new_object.save()
            deactivate_all()

        return new_object

    def calculate_risk(impact, threat_value, vulnerability_value, factor):
        risk_value = impact * threat_value * vulnerability_value if factor else -1
        return max(risk_value, -1)

    def generate_combined_uuid(array_uuid: List[str]) -> uuid.UUID:
        combined = "".join(str(i_uuid) for i_uuid in array_uuid)
        new_uuid = uuid.uuid3(uuid.NAMESPACE_DNS, combined)

        return str(new_uuid)

    def create_service_stat(service_data, is_update=False):
        new_service_asset = create_translations(AssetData, service_data, "label")
        service_stat, created = ServiceStat.objects.get_or_create(
            service=new_service_asset,
            company_reporting=company_reporting_obj,
        )
        if not created and is_update:
            ServiceStat.objects.filter(
                service=new_service_asset, company_reporting=company_reporting_obj
            ).update(
                total_risks=0,
                total_untreated_risks=0,
                total_treated_risks=0,
                total_reduced_risks=0,
                total_denied_risks=0,
                total_accepted_risks=0,
                total_shared_risks=0,
                total_high_risks_treated=0,
                avg_high_risk_treated=0,
                avg_residual_risks=0,
            )

        return service_stat

    def update_service_stat(service_data):
        new_service_asset = create_translations(AssetData, service_data, "label")
        service_stat_exists = ServiceStat.objects.filter(
            service=new_service_asset, company_reporting=company_reporting_obj
        ).exists()
        if service_stat_exists:
            ServiceStat.objects.filter(
                service=new_service_asset, company_reporting=company_reporting_obj
            ).update(
                total_risks=0,
                total_untreated_risks=0,
                total_treated_risks=0,
                total_reduced_risks=0,
                total_denied_risks=0,
                total_accepted_risks=0,
                total_shared_risks=0,
                total_high_risks_treated=0,
                avg_high_risk_treated=0,
                avg_residual_risks=0,
            )

    def update_average(current_avg, treated_risks, new_risks_values):
        if len(new_risks_values) > 0:
            total_risks = treated_risks + len(new_risks_values)
            weighted_sum = (current_avg * treated_risks) + sum(new_risks_values)
            return weighted_sum / total_risks
        return current_avg

    def extract_risks(instance_data):
        instance = instance_data["instance"]
        instance["uuid"] = generate_combined_uuid(
            [instance["asset"], instance["object"], instance["parent_uuid"]]
        )
        risks = instance_data.get("risks", [])

        if risks:
            max_risk_values = []
            treatment_values = []
            residual_risk_values = []
            service_stat = create_service_stat(root_service_data)
            new_asset = create_translations(AssetData, instance, "label")

            for risk in risks.values():
                risk_amv_uuid = (
                    risk["amv"]
                    if risk["amv"]
                    else risk["threat"] + risk["vulnerability"]
                )
                risk_uuid = generate_combined_uuid([instance["uuid"], risk_amv_uuid])
                vulnerability_data = instance_data["vuls"][str(risk["vulnerability"])]
                threat_data = instance_data["threats"][str(risk["threat"])]
                new_vulnerability = create_translations(
                    VulnerabilityData, vulnerability_data, "label"
                )
                new_threat = create_translations(ThreatData, threat_data, "label")
                threat_value = risk["threatRate"]
                vulnerability_value = risk["vulnerabilityRate"]

                impact_c = instance["c"]
                impact_i = instance["i"]
                impact_a = instance["d"]

                risk_c = calculate_risk(
                    impact_c, threat_value, vulnerability_value, threat_data["c"]
                )
                risk_i = calculate_risk(
                    impact_i, threat_value, vulnerability_value, threat_data["i"]
                )
                risk_a = calculate_risk(
                    impact_a, threat_value, vulnerability_value, threat_data["a"]
                )

                max_risk = risk["cacheMaxRisk"]
                if max_risk != -1 and risk["kindOfMeasure"] != 5:
                    max_risk_values.append(max_risk)
                residual_risk = risk["cacheTargetedRisk"]
                if residual_risk != -1 and risk["kindOfMeasure"] != 5:
                    residual_risk_values.append(residual_risk)
                treatment = TREATMENT_VALUES.get(risk["kindOfMeasure"], "Unknown")
                treatment_values.append(risk["kindOfMeasure"])
                recommendations = instance_data.get("recos", [])
                risks_recommendations = (
                    recommendations.get(str(risk["id"]), []) if recommendations else []
                )

                risk_data_object, created = RiskData.objects.update_or_create(
                    uuid=risk_uuid,
                    service=service_stat,
                    defaults={
                        "asset": new_asset,
                        "threat": new_threat,
                        "threat_value": threat_value,
                        "vulnerability": new_vulnerability,
                        "vulnerability_value": vulnerability_value,
                        "residual_risk_level_value": residual_risk,
                        "risk_treatment": treatment,
                        "max_risk": max_risk,
                        "risk_c": risk_c,
                        "risk_i": risk_i,
                        "risk_a": risk_a,
                        "impact_c": impact_c,
                        "impact_i": impact_i,
                        "impact_a": impact_a,
                    },
                )

                if risks_recommendations:
                    for recommendation in risks_recommendations.values():
                        (
                            new_recommendation,
                            created,
                        ) = RecommendationData.objects.update_or_create(
                            uuid=recommendation["uuid"],
                            defaults={
                                "code": recommendation["code"],
                                "description": recommendation["description"],
                                "due_date": recommendation["duedate"],
                                "status": recommendation["status"],
                            },
                        )
                        if created:
                            risk_data_object.recommendations.add(new_recommendation)

            treatment_counts = Counter(treatment_values)

            service_stat.avg_current_risks = update_average(
                service_stat.avg_current_risks,
                service_stat.total_treated_risks,
                max_risk_values,
            )
            service_stat.avg_residual_risks = update_average(
                service_stat.avg_residual_risks,
                service_stat.total_treated_risks,
                residual_risk_values,
            )
            service_stat.total_risks += len(risks)
            service_stat.total_untreated_risks += treatment_counts.get(5, 0)
            service_stat.total_treated_risks += len(risks) - treatment_counts.get(5, 0)
            service_stat.total_reduced_risks += treatment_counts.get(1, 0)
            service_stat.total_denied_risks += treatment_counts.get(2, 0)
            service_stat.total_accepted_risks += treatment_counts.get(3, 0)
            service_stat.total_shared_risks += treatment_counts.get(4, 0)
            service_stat.save()

        # Process child instances recursively
        childrens = instance_data.get("children", [])
        if childrens:
            for child_data in childrens.values():
                child_data["instance"]["parent_uuid"] = instance["uuid"]
                extract_risks(child_data)

    try:
        json_file.seek(0)
        content = json_file.read().decode("utf-8")
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValidationError(f"Error decoding JSON: {str(e)}")

    for instance_data in data["instances"].values():
        instance = instance_data["instance"]
        root_childrens = instance_data.get("children", [])
        if instance["root"] == 0 and instance["parent"] == 0 and root_childrens:
            instance["uuid"] = generate_combined_uuid(
                [instance["asset"], instance["object"]]
            )
            root_service_data = instance.copy()
            instance_data["instance"]["parent_uuid"] = instance["uuid"]
            if is_update:
                update_service_stat(root_service_data)
            extract_risks(instance_data)


def get_pdf_report(request: HttpRequest, cleaned_data: dict):
    static_dir = settings.STATIC_ROOT
    so_data = get_so_data(cleaned_data)
    risk_data = get_risk_data(cleaned_data)
    charts = {
        "colorbar": generate_colorbar(),
        "security_measures_1": generate_bar_chart(
            so_data["bar_chart_data_by_level"], so_data["maturity_levels"]
        ),
        "security_measures_5a": generate_radar_chart(
            so_data["radar_chart_data_by_domain"],
            so_data["domains"],
            so_data["maturity_levels"],
        ),
        "security_measures_5b": generate_radar_chart(
            so_data["radar_chart_data_by_year"],
            so_data["unique_codes_list"],
            so_data["maturity_levels"],
        ),
        "risks_1": generate_bar_chart(
            risk_data["data_by_risk_average"], risk_data["operator_services_with_all"]
        ),
        "risks_2": generate_bar_chart(
            risk_data["data_by_high_risk_rate"], risk_data["operator_services"], True
        ),
        "risks_3": generate_bar_chart(
            risk_data["data_by_high_risk_average"],
            risk_data["operator_services_with_all"],
        ),
        "risks_4": generate_bar_chart(
            risk_data["data_evolution_highest_risks"],
            ["Ra1", "Ra2", "Ra3", "Ra4", "Ra5"],
        ),
    }

    output_from_parsed_template = render_to_string(
        "reporting/template.html",
        {
            "company": cleaned_data["company"],
            "year": cleaned_data["year"],
            "sector": cleaned_data["sector"],
            "report_recommendations": cleaned_data["report_recommendations"],
            "charts": charts,
            "so_data": so_data,
            "nb_years": cleaned_data["nb_years"],
            "service_color_palette": pc.DEFAULT_PLOTLY_COLORS,
            "static_dir": os.path.abspath(static_dir),
        },
        request=request,
    )

    htmldoc = HTML(string=output_from_parsed_template)
    stylesheets = [
        CSS(os.path.join(static_dir, "css/custom.css")),
        CSS(os.path.join(static_dir, "css/report.css")),
    ]

    pdf_buffer = io.BytesIO()
    htmldoc.write_pdf(pdf_buffer, stylesheets=stylesheets)
    pdf_buffer.seek(0)

    return pdf_buffer


def validate_json_file(file):
    if not file.name.endswith(".json"):
        raise ValidationError(_("Uploaded file is not a JSON file."))

    try:
        json_data = json.load(file)
    except json.JSONDecodeError:
        raise ValidationError(_("Uploaded file contains invalid JSON."))

    if not isinstance(json_data, dict):
        raise ValidationError(_("JSON file must contain an object at the root."))

    if "instances" not in json_data:
        raise ValidationError(_("Missing 'instances' key in the JSON file."))

    return json_data


def validate_url_arguments(request, company_id, sector_id, year):
    try:
        company = Company.objects.get(id=company_id)
    except Company.DoesNotExist:
        messages.error(
            request,
            _("No company found"),
        )
        return redirect("reporting")

    try:
        sector = Sector.objects.get(id=sector_id)
    except Sector.DoesNotExist:
        messages.error(
            request,
            _("No sector found"),
        )
        return redirect("reporting")

    try:
        year = int(year)
    except ValueError:
        messages.error(
            request,
            _("Year value is not a valid number"),
        )
        return redirect("reporting")

    current_year = timezone.now().year
    if year < 2020 or year > current_year:
        messages.error(
            request,
            _("Invalid year. Please provide a valid year."),
        )
        return redirect("reporting")

    return company, sector, year


def add_new_report_recommendations(company, sector, year, report_recommendations):
    company_reporting_obj, created = CompanyReporting.objects.get_or_create(
        company=company, year=year, sector=sector
    )
    observation_obj, created = Observation.objects.get_or_create(
        company_reporting=company_reporting_obj
    )
    observation_obj.observation_recommendations.add(*report_recommendations)

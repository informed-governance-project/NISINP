import datetime
import json
import logging
import os
import uuid
from collections import Counter, defaultdict
from urllib.parse import quote as urlquote

from celery import chain, group
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Count
from django.forms.models import model_to_dict
from django.http import (
    FileResponse,
    Http404,
    HttpRequest,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import activate, deactivate_all, gettext
from django.utils.translation import gettext_lazy as _
from django_otp.decorators import otp_required

from governanceplatform.helpers import get_sectors_grouped, user_in_group
from governanceplatform.models import Company, Sector
from securityobjectives.models import StandardAnswer

from .filters import CompanyFilter, RecommendationFilter
from .forms import (
    CompanySelectFormSet,
    ConfigurationReportForm,
    ImportRiskAnalysisForm,
    ObservationRecommendationOrderForm,
    RecommendationsSelectFormSet,
    ReviewCommentForm,
)
from .helpers import create_entry_log, generate_combined_uuid
from .models import (
    AssetData,
    CompanyReporting,
    GeneratedReport,
    LogReporting,
    Observation,
    ObservationRecommendation,
    ObservationRecommendationThrough,
    RecommendationData,
    RiskData,
    SectorReportConfiguration,
    ServiceStat,
    ThreatData,
    VulnerabilityData,
)
from .tasks import generate_pdf_data, generate_pdf_task, save_pdf_task, zip_pdfs_task

# Increasing weasyprint log level
for logger_name in ["weasyprint", "fontTools"]:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.ERROR)


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

    company_filter_list = company_filter.qs

    per_page = reporting_filter_params.get("per_page", 10)
    page_number = reporting_filter_params.get("page")
    paginator = Paginator(company_filter_list, per_page)
    page_obj = paginator.get_page(page_number)

    is_filtered = {
        k: v
        for k, v in reporting_filter_params.items()
        if k not in ["page", "per_page"]
    }

    if request.method == "POST":
        formset = CompanySelectFormSet(
            request.POST,
            queryset=company_filter.qs,
            year=year,
            sectors_filter=sectors_filters,
        )
        if formset.is_valid():
            user_sectors = user.get_sectors().all()
            selected_companies = [
                {
                    "company": form.cleaned_data.get("id"),
                    "sector": form.cleaned_data.get("sector"),
                }
                for form in formset
                if form.cleaned_data.get("selected")
            ]
            is_multiple_selected_companies = len(selected_companies) > 1
            error_messages = []
            errors = 0
            pdf_tasks = []
            run_id = (
                datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                + "_"
                + str(uuid.uuid4())[:8]
            )
            for select_company in selected_companies:
                company = select_company.get("company")
                sector = select_company.get("sector")
                if sector not in user_sectors:
                    if is_multiple_selected_companies:
                        error_message = _("%(sector)s forbidden") % {"sector": sector}
                        error_messages.append(error_message)
                        continue
                    else:
                        messages.error(request, _("Forbidden"))
                        rendered_messages = render_error_messages(request)
                        return JsonResponse({"messages": rendered_messages}, status=400)

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
                        rendered_messages = render_error_messages(request)
                        return JsonResponse({"messages": rendered_messages}, status=400)

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
                        error_message = gettext("No configuration for sector")
                        error_messages.append(error_message)
                        continue
                    else:
                        messages.error(
                            request,
                            _("No configuration for sector"),
                        )
                        rendered_messages = render_error_messages(request)
                        return JsonResponse({"messages": rendered_messages}, status=400)

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
                    rendered_messages = render_error_messages(request)
                    return JsonResponse({"messages": rendered_messages}, status=400)

                report_recommendations = company.get_report_recommandations(
                    year, sector
                )

                report_data = {
                    "company": model_to_dict(
                        company, exclude=["phone_number", "entity_categories"]
                    ),
                    "sector": {**model_to_dict(sector), "name": str(sector)},
                    "year": year,
                    "threshold_for_high_risk": threshold_for_high_risk,
                    "top_ranking": top_ranking,
                    "nb_years": nb_years,
                    "so_excluded": [model_to_dict(so) for so in so_excluded],
                    "report_recommendations": [
                        {
                            **model_to_dict(rec, exclude=["sectors"]),
                            "description": rec.observation_recommendation.description,
                        }
                        for rec in report_recommendations
                    ],
                    "company_reporting": model_to_dict(company_reporting),
                }

                # try:
                sector_name = sector.get_safe_translation()
                filename = urlquote(
                    f"{_('annual_report')}_{year}_{company.name}_{sector_name}.pdf"
                )
                pdf_task = get_pdf_report(
                    request,
                    report_data,
                    run_id,
                    company_reporting,
                    filename,
                    is_multiple_selected_companies,
                )
                pdf_tasks.append(pdf_task)

            if error_messages and not pdf_tasks:
                for error_message in error_messages:
                    messages.error(request, error_message)
                rendered_messages = render_error_messages(request)
                return JsonResponse({"messages": rendered_messages}, status=400)

            success_message = _(
                "Report is being generated. It will be available shortly in the Download Center."
            )

            if is_multiple_selected_companies:
                chain(group(pdf_tasks), zip_pdfs_task.s(user.id, error_messages))()
                success_message = _(
                    "Reports are being generated. They will be available shortly in the Download Center."
                )

            messages.success(request, success_message)
            rendered_messages = render_error_messages(request)

            return JsonResponse({"messages": rendered_messages}, status=202)

    formset = CompanySelectFormSet(
        queryset=page_obj.object_list, year=year, sectors_filter=sectors_filters
    )

    context = {
        "formset": formset,
        "filter": company_filter,
        "is_filtered": bool(is_filtered),
        "pagination_data": page_obj,
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

            if cleaned_data["sector"] not in user_sectors:
                messages.error(request, _("Forbidden"))
                return redirect("report_configuration")

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
    user_sectors = user.get_sectors().all()

    try:
        report_configuration = SectorReportConfiguration.objects.get(
            pk=report_configuration_id
        )
    except SectorReportConfiguration.DoesNotExist:
        messages.error(request, _("Configuration not found"))
        return redirect("report_configuration")

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
    forms = []
    for recommendation in report_recommendations:
        forms.append(ObservationRecommendationOrderForm(instance=recommendation))

    context = {
        "recommendations": forms,
        "company": company,
        "sector": sector,
        "year": year,
    }

    return render(request, "reporting/recommendations.html", context=context)


@login_required
@otp_required
def add_report_recommendations(request, company_id, sector_id, year):
    user = request.user
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
    recommendations_ids = [
        rec.observation_recommendation.id for rec in report_recommendations
    ]

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
                company, sector, year, selected_recommendations, user
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
    user = request.user
    validate_result = validate_url_arguments(request, company_id, sector_id, year)
    if isinstance(validate_result, HttpResponseRedirect):
        return validate_result
    company, sector, year = validate_result
    last_year = year - 1
    report_recommendations = company.get_report_recommandations(last_year, sector)

    if not report_recommendations:
        messages.error(
            request,
            _(f"No recommendations from {last_year}"),
        )
    else:
        add_new_report_recommendations(
            company, sector, year, report_recommendations, user, "COPY"
        )
        messages.success(
            request,
            _(f"Recommendations have been copied from {last_year}"),
        )

    redirect_url = reverse("report_recommendations", args=[company_id, sector_id, year])

    return redirect(redirect_url)


@login_required
@otp_required
def delete_report_recommendation(request, company_id, sector_id, year, report_rec_id):
    user = request.user
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
    create_entry_log(user, company_reporting, "DELETE RECOMMENDATIONS")

    return redirect(redirect_url)


@login_required
@otp_required
def update_report_recommendation(request, report_rec_id):
    try:
        report_recommendation = ObservationRecommendationThrough.objects.get(
            id=report_rec_id
        )
    except ObservationRecommendationThrough.DoesNotExist:
        return JsonResponse({"error": "Observation not found."}, status=404)

    if request.method == "POST":
        form = ObservationRecommendationOrderForm(
            request.POST, instance=report_recommendation
        )
        if form.is_valid():
            form.save()
            return JsonResponse({"success": True})

    messages.error(request, _("Forbidden"))
    return redirect("reporting")


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

    try:
        initial = {}
        if "company_id" in request.GET:
            company_id = int(request.GET.get("company_id"))
            if not companies_queryset.filter(id=company_id).exists():
                messages.error(request, _("Forbidden"))
                return HttpResponseRedirect(request.headers.get("referer"))
            initial["company"] = company_id

        if "sector_id" in request.GET:
            sector_id = int(request.GET.get("sector_id"))
            if not sectors_queryset.filter(id=sector_id).exists():
                messages.error(request, _("Forbidden"))
                return HttpResponseRedirect(request.headers.get("referer"))
            initial["sectors"] = sector_id

        if "year" in request.GET:
            initial["year"] = int(request.GET.get("year"))

    except (ValueError, TypeError):
        messages.error(request, _("Invalid request"))
        return HttpResponseRedirect(request.headers.get("referer"))

    choices = {
        "company": company_list,
        "sectors": sector_list,
    }

    if request.method == "POST":
        form = ImportRiskAnalysisForm(
            request.POST,
            request.FILES,
            initial=initial or {},
            choices=choices,
        )
        if form.is_valid():
            json_file = form.cleaned_data["import_file"]
            company_id = form.cleaned_data["company"]
            sector_ids = form.cleaned_data["sectors"]
            year = form.cleaned_data["year"]
            try:
                validate_json_file(json_file)
            except ValidationError as e:
                messages.error(request, f"Error: {str(e)}")
                return HttpResponseRedirect(request.headers.get("referer"))

            for sector_id in sector_ids:
                validate_result = validate_url_arguments(
                    request, company_id, sector_id, year
                )
                if isinstance(validate_result, HttpResponseRedirect):
                    return HttpResponseRedirect(request.headers.get("referer"))

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
                if not created:
                    report_recommendations = list(
                        ObservationRecommendationThrough.objects.filter(
                            observation__company_reporting=company_reporting_obj
                        )
                    )
                    logs = list(
                        LogReporting.objects.filter(reporting=company_reporting_obj)
                    )

                    comment = (
                        str(company_reporting_obj.comment)
                        if company_reporting_obj.comment
                        else ""
                    )

                    company_reporting_obj.delete()
                    company_reporting_obj = CompanyReporting.objects.create(
                        company=company, year=year, sector=sector, comment=comment
                    )

                    if logs:
                        new_logs = [
                            LogReporting(
                                reporting=company_reporting_obj,
                                user=log.user,
                                user_full_name=log.user_full_name,
                                action=log.action,
                                timestamp=log.timestamp,
                            )
                            for log in logs
                        ]
                        LogReporting.objects.bulk_create(new_logs)

                    if report_recommendations:
                        add_new_report_recommendations(
                            company, sector, year, report_recommendations, user, "COPY"
                        )

                try:
                    parsing_risk_data_json(json_file, company_reporting_obj)
                except Exception as e:
                    messages.error(request, f"Parsing error: {str(e)}")
                    return HttpResponseRedirect(request.headers.get("referer"))

                messages.success(request, _("Risk analysis successfully imported"))
                create_entry_log(user, company_reporting_obj, "RISK ANALYSIS IMPORT")
                return HttpResponseRedirect(request.headers.get("referer"))

    form = ImportRiskAnalysisForm(
        initial=initial or {},
        choices=choices,
    )
    context = {"form": form}
    return render(request, "modals/risk_analysis_import.html", context=context)


@login_required
@otp_required
def access_log(request, company_id, sector_id, year):
    validate_result = validate_url_arguments(request, company_id, sector_id, year)
    if isinstance(validate_result, HttpResponseRedirect):
        return validate_result
    company, sector, year = validate_result
    try:
        company_reporting = CompanyReporting.objects.get(
            company=company, year=year, sector=sector
        )
        log = LogReporting.objects.filter(reporting=company_reporting).order_by(
            "-timestamp"
        )
    except CompanyReporting.DoesNotExist:
        log = LogReporting.objects.none()

    context = {"log": log}
    return render(request, "modals/reporting_access_log.html", context=context)


@login_required
@otp_required
def review_comment_report(request, company_id, sector_id, year):
    user = request.user
    validate_result = validate_url_arguments(request, company_id, sector_id, year)
    if isinstance(validate_result, HttpResponseRedirect):
        return validate_result
    company, sector, year = validate_result
    try:
        company_reporting = CompanyReporting.objects.get(
            company=company, year=year, sector=sector
        )
    except CompanyReporting.DoesNotExist:
        return render(request, "reporting/dashboard.html", {})

    if request.method == "POST":
        form = ReviewCommentForm(request.POST, instance=company_reporting)
        if form.is_valid():
            form.save()
            create_entry_log(user, company_reporting, "ADD COMMENT")
            return redirect("reporting")
    else:
        form = ReviewCommentForm(instance=company_reporting)

    context = {
        "form": form,
        "company": company,
        "sector": sector,
        "year": year,
    }

    return render(request, "modals/review_comment_report.html", context=context)


@login_required
@otp_required
def download_center(request):
    reports = GeneratedReport.objects.filter(user=request.user).order_by("-timestamp")
    return render(request, "reporting/download_center.html", {"reports": reports})


@login_required
@otp_required
def download_report(request, file_uuid):
    try:
        report = GeneratedReport.objects.get(file_uuid=file_uuid, user=request.user)
        file_path = report.get_file_path()
        return FileResponse(
            open(file_path, "rb"), as_attachment=True, filename=report.filename
        )
    except (GeneratedReport.DoesNotExist, FileNotFoundError):
        raise Http404("Report not found.")


def parsing_risk_data_json(json_file, company_reporting_obj):
    LANG_VALUES = {1: "fr", 2: "en", 3: "de", 4: "nl"}
    TREATMENT_VALUES = {
        1: "REDUC",
        2: "DENIE",
        3: "ACCEP",
        4: "SHARE",
        5: "UNTRE",
    }

    def extract_risks(instance):
        def create_translations(class_model, values, field_name):
            new_object, created = class_model.objects.get_or_create(uuid=values["uuid"])

            if created:
                translations = values.get(field_name, None)
                if not translations:
                    return new_object

                if is_new_version and languageCode:
                    activate(languageCode)
                    new_object.set_current_language(languageCode)
                    new_object.name = translations
                else:
                    for lang_index, lang_code in LANG_VALUES.items():
                        name_value = translations.get(
                            field_name + str(lang_index), None
                        )
                        if name_value:
                            activate(lang_code)
                            new_object.set_current_language(lang_code)
                            new_object.name = name_value

                new_object.save()
                deactivate_all()

            return new_object

        def create_service_stat(service_data):
            new_service_asset = create_translations(AssetData, service_data, "label")
            service_stat, _created = ServiceStat.objects.get_or_create(
                service=new_service_asset,
                company_reporting=company_reporting_obj,
            )

            return service_stat

        def update_average(current_avg, treated_risks, new_risks_values):
            if len(new_risks_values) > 0:
                total_risks = treated_risks + len(new_risks_values)
                weighted_sum = (current_avg * treated_risks) + sum(new_risks_values)
                return weighted_sum / total_risks
            return current_avg

        def generate_information_risk_uuid(risk):
            return (
                risk["informationRisk"]["uuid"]
                if risk["informationRisk"]
                else risk["threat"]["uuid"] + risk["vulnerability"]["uuid"]
            )

        def calculate_risks(risk):
            def get_risk_value(risk_value, factor):
                risk_value = risk_value if factor else -1
                return max(risk_value, -1)

            threat = risk["threat"]

            return {
                "riskConfidentiality": get_risk_value(
                    risk["riskIntegrity"], threat["confidentiality"]
                ),
                "riskIntegrity": get_risk_value(
                    risk["riskIntegrity"], threat["integrity"]
                ),
                "riskAvailability": get_risk_value(
                    risk["riskAvailability"], threat["availability"]
                ),
            }

        risks = instance["instanceRisks"]
        children = instance["children"]

        if risks:
            max_risk_values = []
            treatment_values = []
            residual_risk_values = []
            service_stat = create_service_stat(root_service_data)
            new_asset = create_translations(AssetData, instance, "label")

            for risk in risks:
                information_risk_uuid = generate_information_risk_uuid(risk)

                new_vulnerability = create_translations(
                    VulnerabilityData, risk["vulnerability"], "label"
                )

                new_threat = create_translations(ThreatData, risk["threat"], "label")
                risk_values = calculate_risks(risk)
                risk.update(risk_values)
                risk.update(
                    {
                        "uuid": generate_combined_uuid(
                            [instance["uuid"], information_risk_uuid]
                        ),
                        "risk_treatment": TREATMENT_VALUES.get(
                            risk["kindOfMeasure"], "Unknown"
                        ),
                    }
                )

                if risk["cacheMaxRisk"] != -1 and risk["kindOfMeasure"] != 5:
                    max_risk_values.append(risk["cacheMaxRisk"])
                if risk["cacheTargetedRisk"] != -1 and risk["kindOfMeasure"] != 5:
                    residual_risk_values.append(risk["cacheTargetedRisk"])

                treatment_values.append(risk["kindOfMeasure"])

                risk_data_object, created = RiskData.objects.update_or_create(
                    uuid=risk["uuid"],
                    service=service_stat,
                    defaults={
                        "asset": new_asset,
                        "threat": new_threat,
                        "threat_value": risk["threatRate"],
                        "vulnerability": new_vulnerability,
                        "vulnerability_value": risk["vulnerabilityRate"],
                        "residual_risk": risk["cacheTargetedRisk"],
                        "risk_treatment": risk["risk_treatment"],
                        "max_risk": risk["cacheMaxRisk"],
                        "risk_c": risk["riskConfidentiality"],
                        "risk_i": risk["riskIntegrity"],
                        "risk_a": risk["riskAvailability"],
                        "impact_c": instance["confidentiality"],
                        "impact_i": instance["integrity"],
                        "impact_a": instance["availability"],
                    },
                )

                for recommendation in risk["recommendations"]:
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
        for child in children:
            normalized_instance = get_normalized_instance(child)
            normalized_instance["parent_uuid"] = instance["uuid"]
            extract_risks(normalized_instance)

    def is_root_instance(instance):
        children = instance.get("children", [])
        if is_new_version:
            is_root = instance.get("level") == 1 and instance.get("position") == 1
        else:
            meta_instance = instance.get("instance", {})
            is_root = (
                meta_instance.get("root") == 0 and meta_instance.get("parent") == 0
            )

        return is_root and bool(children)

    def get_normalized_instance(instance):
        def get_translations_dict(values, field_name):
            translations_dict = {}
            for lang_index in LANG_VALUES.keys():
                key = field_name + str(lang_index)
                name_value = values.get(key, None)
                if name_value:
                    translations_dict[key] = name_value
            return translations_dict

        def get_normalized_threat(instance_risk, threats):
            threat_data = threats.get(str(instance_risk["threat"]), {})
            threat_data["confidentiality"] = threat_data.get("c")
            threat_data["integrity"] = threat_data.get("i")
            threat_data["availability"] = threat_data.get("a")
            threat_data["label"] = get_translations_dict(threat_data, "label")
            threat_data["description"] = get_translations_dict(
                threat_data, "description"
            )
            return threat_data

        def get_normalized_vulnerability(instance_risk, vuls):
            vulnerability_data = vuls.get(str(instance_risk["vulnerability"]), {})
            vulnerability_data["label"] = get_translations_dict(
                vulnerability_data, "label"
            )
            vulnerability_data["description"] = (
                get_translations_dict(vulnerability_data, "description"),
            )
            return vulnerability_data

        if is_new_version:
            normalized_instance = instance.copy()
            asset_uuid = instance["asset"]["uuid"]
            object_uuid = instance["object"]["uuid"]
            parent_uuid = instance.get("parent_uuid", "")
            normalized_instance["uuid"] = generate_combined_uuid(
                [asset_uuid, object_uuid, parent_uuid]
            )

        else:
            normalized_instance = defaultdict()
            meta_instance = instance["instance"]
            asset_uuid = meta_instance["asset"]
            object_uuid = meta_instance["object"]
            parent_uuid = instance.get("parent_uuid", "")
            risks_data = instance.get("risks", {})
            risks = risks_data if isinstance(risks_data, dict) else {}
            children_data = instance.get("children", {})
            children = children_data if isinstance(children_data, dict) else {}
            instance_risks = risks.values()
            amvs = instance.get("amvs", {})
            threats = instance.get("threats", {})
            vuls = instance.get("vuls", {})
            recos_data = instance.get("recos", {})
            recos = recos_data if isinstance(recos_data, dict) else {}

            for instance_risk in instance_risks:
                txv = instance_risk["threatRate"] * instance_risk["vulnerabilityRate"]
                recommendation_data = recos.get(str(instance_risk["id"]), {})

                instance_risk.update(
                    {
                        "informationRisk": amvs.get(str(instance_risk["amv"]), {}),
                        "threat": get_normalized_threat(instance_risk, threats),
                        "vulnerability": get_normalized_vulnerability(
                            instance_risk, vuls
                        ),
                        "recommendations": recommendation_data.values(),
                        "riskConfidentiality": instance["instance"]["c"] * txv,
                        "riskIntegrity": instance["instance"]["i"] * txv,
                        "riskAvailability": instance["instance"]["d"] * txv,
                    }
                )

            normalized_instance.update(
                {
                    "uuid": generate_combined_uuid(
                        [asset_uuid, object_uuid, parent_uuid]
                    ),
                    "name": get_translations_dict(meta_instance, "name"),
                    "label": get_translations_dict(meta_instance, "label"),
                    "confidentiality": instance["instance"]["c"],
                    "integrity": instance["instance"]["i"],
                    "availability": instance["instance"]["d"],
                    "instanceRisks": instance_risks,
                    "children": children.values(),
                }
            )

        return normalized_instance

    try:
        json_file.seek(0)
        content = json_file.read().decode("utf-8")
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValidationError(f"Error decoding JSON: {str(e)}")

    file_version = tuple(map(int, data["monarc_version"].split(".")))
    refactoring_version = tuple(map(int, "2.13.1".split(".")))
    is_new_version = file_version >= refactoring_version
    languageCode = data.get("languageCode", None)

    instances = data["instances"] if is_new_version else data["instances"].values()

    for instance in instances:
        if is_root_instance(instance):
            normalized_instance = get_normalized_instance(instance)
            root_service_data = normalized_instance.copy()
            normalized_instance["parent_uuid"] = normalized_instance["uuid"]
            extract_risks(normalized_instance)


def get_pdf_report(
    request: HttpRequest,
    cleaned_data: dict,
    run_id,
    company_reporting,
    filename,
    is_multiple_files: bool,
):
    user = request.user
    static_dir = settings.STATIC_ROOT

    stylesheets = [
        os.path.join(static_dir, "css/custom.css"),
        os.path.join(static_dir, "css/report.css"),
    ]

    # Send the pdf to celery
    pdf_task = chain(
        generate_pdf_data.s(cleaned_data),
        generate_pdf_task.s(stylesheets),
        save_pdf_task.s(
            run_id, user.id, company_reporting.id, filename, is_multiple_files
        ),
    )
    if not is_multiple_files:
        return pdf_task.delay()

    return pdf_task


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
    user = request.user
    user_sectors = user.get_sectors().all()

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

    if sector not in user_sectors:
        messages.error(request, _("Forbidden"))
        return redirect("reporting")

    return company, sector, year


def add_new_report_recommendations(
    company, sector, year, report_recommendations, user, action="ADD"
):
    company_reporting_obj, created = CompanyReporting.objects.get_or_create(
        company=company, year=year, sector=sector
    )
    observation_obj, created = Observation.objects.get_or_create(
        company_reporting=company_reporting_obj
    )
    if action == "ADD":
        observation_obj.observation_recommendations.add(*report_recommendations)

        create_entry_log(user, company_reporting_obj, "ADD RECOMMENDATIONS")
    elif action == "COPY":
        new_report_recommendations = [
            ObservationRecommendationThrough(
                observation=observation_obj,
                observation_recommendation=rec.observation_recommendation,
                order=rec.order,
            )
            for rec in report_recommendations
        ]

        ObservationRecommendationThrough.objects.bulk_create(new_report_recommendations)

    create_entry_log(user, company_reporting_obj, f"{action} RECOMMENDATIONS")


def render_error_messages(request):
    return render_to_string(
        "django_bootstrap5/messages.html",
        {"messages": messages.get_messages(request)},
        request=request,
    )

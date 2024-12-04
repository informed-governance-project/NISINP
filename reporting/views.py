import base64
import io
import json
import os
import textwrap
import uuid
import zipfile
from collections import Counter, OrderedDict, defaultdict
from io import BytesIO
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
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils.translation import activate, deactivate_all
from django.utils.translation import gettext_lazy as _
from django_otp.decorators import otp_required
from weasyprint import CSS, HTML

from governanceplatform.helpers import get_sectors_grouped, user_in_group
from governanceplatform.models import Company, Sector
from reporting.models import (
    AssetData,
    RecommendationData,
    RiskData,
    ServiceStat,
    ThreatData,
    VulnerabilityData,
)
from securityobjectives.models import (
    Domain,
    MaturityLevel,
    SecurityObjective,
    SecurityObjectivesInStandard,
    SecurityObjectiveStatus,
    StandardAnswer,
)

from .filters import CompanyFilter
from .forms import CompanySelectFormSet, ImportRiskAnalysisForm, ReportGenerationForm

SERVICES_COLOR_PALETTE = pc.DEFAULT_PLOTLY_COLORS

SO_COLOR_PALETTE = [
    (0, "#F8696B"),
    (0.5, "#FA9473"),
    (1, "#FCBF7B"),
    (1.5, "#FFEB84"),
    (2, "#CCDD82"),
    (2.5, "#98CE7F"),
    (3, "#63BE7B"),
]

OPERATOR_SERVICES = [
    "All services",
    "Fixed data",
    "Fixed voice",
    "Mobile data",
    "Mobile voice",
]


@login_required
@otp_required
def reporting(request):
    user = request.user
    if request.method == "POST":
        formset = CompanySelectFormSet(request.POST)
        if formset.is_valid():
            selected_companies = [
                form.instance for form in formset if form.cleaned_data.get("selected")
            ]
            year = 2023
            nb_years = 3

            if len(selected_companies) > 1:
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                    for company in selected_companies:
                        sectors = company.get_queryset_sectors()
                        for sector in sectors:
                            security_objectives_declaration = (
                                StandardAnswer.objects.filter(
                                    submitter_company=company,
                                    sectors=sector,
                                    year_of_submission=year,
                                    status="PASS",
                                ).order_by("submit_date")
                            )

                            if not security_objectives_declaration:
                                continue

                            report_data = {
                                "company": company,
                                "sector": sector,
                                "year": year,
                                "nb_years": nb_years,
                                "so_excluded": [],
                            }

                            pdf_report = get_pdf_report(request, report_data)
                            sector_name = sector.get_safe_translation()
                            filename = urlquote(
                                f"{_('annual_report')}_{year}_{company.name}_{sector_name}.pdf"
                            )
                            zip_file.writestr(filename, pdf_report.read())

                zip_buffer.seek(0)

                response = HttpResponse(zip_buffer, content_type="application/zip")
                response["Content-Disposition"] = 'attachment; filename="reports.zip"'
            else:
                company = selected_companies[0]
                sectors = company.get_queryset_sectors()
                if sectors.count() > 1:
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                        for sector in sectors:
                            security_objectives_declaration = (
                                StandardAnswer.objects.filter(
                                    submitter_company=company,
                                    sectors=sector,
                                    year_of_submission=year,
                                    status="PASS",
                                ).order_by("submit_date")
                            )

                            if not security_objectives_declaration:
                                messages.error(
                                    request,
                                    _("No data found for security objectives report"),
                                )
                                return redirect("report_generation")

                            report_data = {
                                "company": company,
                                "sector": sector,
                                "year": year,
                                "nb_years": nb_years,
                                "so_excluded": [],
                            }

                            pdf_report = get_pdf_report(request, report_data)
                            sector_name = sector.get_safe_translation()
                            filename = urlquote(
                                f"{_('annual_report')}_{year}_{company.name}_{sector_name}.pdf"
                            )
                            zip_file.writestr(filename, pdf_report.read())
                    zip_buffer.seek(0)
                    response = HttpResponse(zip_buffer, content_type="application/zip")
                    response[
                        "Content-Disposition"
                    ] = 'attachment; filename="reports.zip"'
                else:
                    sector = sectors.first()
                    security_objectives_declaration = StandardAnswer.objects.filter(
                        submitter_company=company,
                        sectors=sector,
                        year_of_submission=year,
                        status="PASS",
                    ).order_by("submit_date")

                    if not security_objectives_declaration:
                        messages.error(
                            request,
                            _("No data found for security objectives report"),
                        )
                        return redirect("report_generation")

                    report_data = {
                        "company": company,
                        "sector": sector,
                        "year": year,
                        "nb_years": nb_years,
                        "so_excluded": [],
                    }
                    pdf_report = get_pdf_report(request, report_data)
                    sector_name = sector.get_safe_translation()
                    filename = urlquote(
                        f"{_('annual_report')}_{year}_{company.name}_{sector_name}.pdf"
                    )
                    response = HttpResponse(pdf_report, content_type="application/pdf")
                    response[
                        "Content-Disposition"
                    ] = f'attachment; filename="{filename}"'

            return response

    companies_queryset = (
        Company.objects.filter(
            companyuser__sectors__in=user.get_sectors().values_list("id", flat=True)
        ).distinct()
        if user_in_group(user, "RegulatorUser")
        else Company.objects.all()
    )

    # Filter
    if "reset" in request.GET:
        if "reporting_filter_params" in request.session:
            del request.session["reporting_filter_params"]
        return redirect("reporting")

    if request.GET:
        request.session["reporting_filter_params"] = request.GET

    reporting_filter_params = request.session.get(
        "reporting_filter_params", request.GET
    )
    company_filter = CompanyFilter(reporting_filter_params, queryset=companies_queryset)

    is_filtered = {k: v for k, v in reporting_filter_params.items() if k != "page"}

    formset = CompanySelectFormSet(queryset=company_filter.qs)

    context = {
        "formset": formset,
        "filter": company_filter,
        "is_filtered": bool(is_filtered),
    }

    return render(request, "reporting/dashboard.html", context)


@login_required
@otp_required
def report_generation(request):
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
    so_queryset = SecurityObjectivesInStandard.objects.filter(
        standard__regulator=user.regulators.first()
    ).order_by("position")

    company_list = [(company.id, str(company)) for company in companies_queryset]
    so_list = [
        (so.security_objective.id, str(so.security_objective)) for so in so_queryset
    ]

    initial = {
        "company": company_list,
        "sectors": sector_list,
        "so": so_list,
    }
    if request.method == "POST":
        form = ReportGenerationForm(request.POST, initial=initial)
        if form.is_valid():
            try:
                company_id = form.cleaned_data["company"]
                sector_id = form.cleaned_data["sector"]
                year = int(form.cleaned_data["year"])
                company = Company.objects.get(pk=company_id)
                sector = Sector.objects.get(pk=sector_id)
            except (Company.DoesNotExist, Sector.DoesNotExist):
                messages.error(
                    request,
                    _("Data not found for generate the report"),
                )
                return redirect("report_generation")

            security_objectives_declaration = StandardAnswer.objects.filter(
                submitter_company=company,
                sectors=sector,
                year_of_submission=year,
                status="PASS",
            ).order_by("submit_date")

            if not security_objectives_declaration:
                messages.error(
                    request,
                    _("No data found for security objectives report"),
                )
                return redirect("report_generation")

            cleaned_data = {
                "company": company,
                "sector": sector,
                "year": year,
                "nb_years": int(form.cleaned_data["nb_years"]),
                "security_objectives_declaration": security_objectives_declaration.last(),
                "so_excluded": form.cleaned_data["so_exclude"],
            }

            pdf_report = get_pdf_report(request, cleaned_data)
            # try:
            #     pdf_report = get_pdf_report(request)
            # except Exception:
            #     messages.warning(request, _("An error occurred while generating the report."))
            #     return HttpResponseRedirect(reverse("incidents"))
            filename = urlquote(
                f"{_('annual_report')}_{year}_{company.name} - {_('annual_report')}"
            )
            response = HttpResponse(pdf_report, content_type="application/pdf")
            response["Content-Disposition"] = f"attachment;filename={filename}.pdf"

            return response

    form = ReportGenerationForm(initial=initial)
    context = {"form": form}
    return render(request, "reporting/report_generation.html", context=context)


# To DO : restrict acces to incidentuser
# @login_required
# @otp_required
# def risk_analysis_submission(request):
#     if request.method == "POST":
#         json_file = request.FILES["data"]
#         try:
#             request.FILES["data"] = validate_json_file(json_file)
#         except ValidationError as e:
#             messages.error(request, f"Error: {str(e)}")
#             return HttpResponseRedirect(reverse("risk_analysis_submission"))

#         form = RiskAnalysisSubmissionForm(request.POST, request.FILES)
#         if form.is_valid():
#             risk_analysis = form.save(commit=False)
#             # TO DO : manage the multiple company stuff
#             risk_analysis.company = get_active_company_from_session(request)
#             risk_analysis.save()

#             parsing_risk_data_json(risk_analysis)

#             messages.success(request, _("Risk Analysis submitted successfully"))

#     form = RiskAnalysisSubmissionForm()

#     return render(
#         request, "operator/reporting/risk_analysis_submission.html", {"form": form}
#     )


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
        files = request.FILES.getlist("files")
        file_messages = {"success": [], "error": []}
        for file in files:
            try:
                validate_json_file(file)
                file_messages["success"].append(
                    f"{file.name}: Risk Analysis submitted successfully"
                )
            except ValidationError as e:
                file_messages["error"].append(f"{file.name}: {str(e)}")

        for message in file_messages["success"]:
            messages.success(request, message)
        for message in file_messages["error"]:
            messages.error(request, message)

    form = ImportRiskAnalysisForm(initial=initial)
    context = {"form": form}
    return render(
        request, "operator/reporting/risk_analysis_submission.html", context=context
    )


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
                    radar_data.setdefault(
                        f"{legend_sector_translation} {current_year}", []
                    ).append(values[sector_avg_field])

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
    legend_sector_translation = _("Sector average")
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
            label=f"{legend_sector_translation} {year}",
        )

        # Sector asc and desc lists by score

        sector_so_by_year_asc[year] = [
            SecurityObjective.objects.get(pk=score["security_objective"])
            for score in sector_scores_queryset.order_by("score_value")
        ]

        sector_so_by_year_desc[year] = list(sector_so_by_year_asc[year])
        sector_so_by_year_desc[year].reverse()

    bar_chart_data_by_level_sorted = sorted(
        bar_chart_data_by_level.items(),
        key=lambda x: (x[0] != legend_sector_translation, x[0]),
    )

    radar_chart_data_by_domain = build_radar_data(company_so_by_domain, "sector_avg")
    radar_chart_data_by_year = build_radar_data(company_so_by_year)

    so_data = {
        "years": years_list,
        "domains": [str(domain) for domain in company_so_by_domain.keys()],
        "maturity_levels": maturity_levels,
        "unique_codes_list": [so.unique_code for so in company_so_by_year.keys()],
        "max_of_company_count": max(company_counts.values()),
        "bar_chart_data_by_level": dict(bar_chart_data_by_level_sorted),
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


def get_data_risks_average():
    data = {
        "Operator 2019": [1.52, 1.42, 1.47, 1.6, 1.58],
        "Operator 2020": [1.52, 1.41, 1.46, 1.6, 1.58],
        "Sector Avg 2019": [2.49, 2.19, 2.33, 2.05, 1.78],
        "Sector Avg 2020": [2.16, 2.19, 2.33, 2.05, 1.78],
    }

    return data


def get_data_high_risks_average():
    data = {
        "Operator 2019": [0, 0, 0, 0, 0],
        "Operator 2020": [0, 0, 0, 0, 0],
        "Sector Avg 2019": [10.82, 11.06, 10.88, 8.62, 9.33],
        "Sector Avg 2020": [8.95, 8.87, 8.83, 9.69, 9],
    }

    return data


def get_data_evolution_highest_risks():
    data = {
        "DummyLux 2023": [18, 12, 12, 9, 8],
        "DummyLux 2024": [12, 12, 3, 4, 8],
    }

    return data


def generate_bar_chart(data, labels):
    fig = go.Figure()
    labels = text_wrap(labels)
    bar_colors_palette = pc.qualitative.Pastel1
    average_colors_palette = pc.qualitative.Set1
    avg_index = 0
    bar_index = 0

    for name, values in data.items():
        group_name = str(name)[-4:]

        if str(_("average")) in name:
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
                    text=values,
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
    # Define the levels and corresponding labels
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

    # Create a dummy trace to generate the color bar
    fig = go.Figure(
        data=go.Scatter(
            x=[None],  # No actual data, this is a dummy trace
            y=[None],
            mode="markers",
            marker=dict(
                size=0,
                color=[-0.1, 3],  # This will dictate the color bar range
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
                    ticktext=labels,  # Use the labels for tick text
                    orientation="h",  # Horizontal color bar
                    x=0.5,  # Center the color bar
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

    # Add the annotations to the figure
    fig.update_layout(annotations=annotations)

    # Hide axis lines and ticks
    fig.update_layout(
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False, range=[0, 1]),
        yaxis=dict(showticklabels=False, showgrid=False, zeroline=False, range=[0, 1]),
        plot_bgcolor="rgba(0,0,0,0)",  # Transparent background
        paper_bgcolor="rgba(0,0,0,0)",  # Transparent paper background
        margin=dict(l=40, r=40, t=200, b=15),  # Adjust margins
        height=50,
    )

    # Remove the grid and axis from the layout
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


def convert_graph_to_base64(fig):
    buffer = BytesIO()
    fig.write_image(buffer, format="png")
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()

    graph = base64.b64encode(image_png)
    graph = graph.decode("utf-8")

    return graph


def parsing_risk_data_json(risk_analysis_json):
    LANG_VALUES = {1: "fr", 2: "en", 3: "de", 4: "nl"}
    TREATMENT_VALUES = {
        1: "REDUC",
        2: "DENIE",
        3: "ACCEP",
        4: "SHARE",
        5: "UNTRE",
    }

    data = risk_analysis_json.data

    def create_translations(class_model, values, field_name):
        new_object, created = class_model.objects.get_or_create(uuid=values["uuid"])

        if created:
            for lang_index, lang_code in LANG_VALUES.items():
                activate(lang_code)
                new_object.set_current_language(lang_code)
                new_object.name = values[field_name + str(lang_index)]

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

    def create_service_stat(service_data):
        new_service_asset = create_translations(AssetData, service_data, "name")
        new_service_stat, created = ServiceStat.objects.get_or_create(
            service=new_service_asset,
            risk_analysis=risk_analysis_json,
        )
        return new_service_stat

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
            new_asset = create_translations(AssetData, instance, "name")

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

                new_risk = RiskData(
                    uuid=risk_uuid,
                    service=service_stat,
                    asset=new_asset,
                    threat=new_threat,
                    threat_value=threat_value,
                    vulnerability=new_vulnerability,
                    vulnerability_value=vulnerability_value,
                    residual_risk_level_value=residual_risk,
                    risk_treatment=treatment,
                    max_risk=max_risk,
                    risk_c=risk_c,
                    risk_i=risk_i,
                    risk_a=risk_a,
                    impact_c=impact_c,
                    impact_i=impact_i,
                    impact_a=impact_a,
                )
                new_risk.save()

                if risks_recommendations:
                    for recommendation in risks_recommendations.values():
                        (
                            new_recommendation,
                            created,
                        ) = RecommendationData.objects.get_or_create(
                            uuid=recommendation["uuid"],
                            defaults={
                                "code": recommendation["code"],
                                "description": recommendation["description"],
                                "due_date": recommendation["duedate"],
                                "status": recommendation["status"],
                            },
                        )
                        new_risk.recommendations.add(new_recommendation)

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

    # Extract the root instances and process them
    for instance_data in data["instances"].values():
        instance = instance_data["instance"]
        root_childrens = instance_data.get("children", [])
        if instance["root"] == 0 and instance["parent"] == 0 and root_childrens:
            instance["uuid"] = generate_combined_uuid(
                [instance["asset"], instance["object"]]
            )
            root_service_data = instance
            instance_data["instance"]["parent_uuid"] = instance["uuid"]
            extract_risks(instance_data)


def get_pdf_report(request: HttpRequest, cleaned_data: dict):
    static_dir = settings.STATIC_ROOT
    so_data = get_so_data(cleaned_data)
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
        "risks_1": generate_bar_chart(get_data_risks_average(), OPERATOR_SERVICES),
        "risks_3": generate_bar_chart(get_data_high_risks_average(), OPERATOR_SERVICES),
        "risks_4": generate_bar_chart(
            get_data_evolution_highest_risks(), ["Ra1", "Ra2", "Ra3", "Ra4", "Ra5"]
        ),
    }

    output_from_parsed_template = render_to_string(
        "reporting/template.html",
        {
            "company": cleaned_data["company"],
            "year": cleaned_data["year"],
            "sector": cleaned_data["sector"],
            "charts": charts,
            "so_data": so_data,
            "nb_years": cleaned_data["nb_years"],
            "service_color_palette": SERVICES_COLOR_PALETTE,
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

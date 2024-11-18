import base64
import json
import os
import random
import textwrap
import uuid
from collections import Counter
from io import BytesIO
from typing import List

import plotly.colors as pc
import plotly.graph_objects as go
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Avg, Count, F, OuterRef, Subquery
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
    SecurityObjectivesInStandard,
    SecurityObjectiveStatus,
    StandardAnswer,
)

from .forms import ImportRiskAnalysisForm, ReportGenerationForm

SERVICES_COLOR_PALETTE = pc.DEFAULT_PLOTLY_COLORS

SO_SOPHISTICATION_LEVELS = [
    str(level) for level in MaturityLevel.objects.order_by("level")
]


SO_DOMAINS = [str(domain) for domain in Domain.objects.order_by("position")]

YEARS = [
    "2022",
    "2023",
    "2024",
]

SO_COLOR_PALETTE = [
    (0, "#F8696B"),
    (0.5, "#FA9473"),
    (1, "#FCBF7B"),
    (1.5, "#FFEB84"),
    (2, "#CCDD82"),
    (2.5, "#98CE7F"),
    (3, "#63BE7B"),
]


SO_LIST = [
    "SO1",
    "SO2",
    "SO3",
    "SO4",
    "SO5",
    "SO6",
    "SO7",
    "SO8",
    "SO9",
    "SO10",
    "SO11",
    "SO12",
    "SO13",
    "SO14",
    "SO15",
    "SO16",
    "SO17",
    "SO18",
    "SO19",
    "SO20",
    "SO21",
    "SO22",
    "SO23",
    "SO24",
    "SO25",
    "SO26",
    "SO27",
    "SO28",
    "SO29",
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
    return render(request, "home/base.html")


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

            response = HttpResponse(pdf_report, content_type="application/pdf")
            response["Content-Disposition"] = "attachment;filename=annual_report.pdf"

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


def get_data_by_so_domains():
    data = {
        "DummyLux 2023": [random.choice(range(4)) for _ in range(len(SO_DOMAINS))],
        "DummyLux 2024": [random.choice(range(4)) for _ in range(len(SO_DOMAINS))],
        "Secteur": [random.choice(range(4)) for _ in range(len(SO_DOMAINS))],
    }

    return data


def get_data_by_so_list():
    data = {
        "DummyLux 2023": [random.choice(range(4)) for _ in range(len(SO_LIST))],
        "DummyLux 2024": [random.choice(range(4)) for _ in range(len(SO_LIST))],
    }

    return data


def get_data_so_average(cleaned_data):
    company = cleaned_data["company"]
    sector = cleaned_data["sector"]
    current_year = cleaned_data["year"]
    nb_years = cleaned_data["nb_years"]
    data = {}
    for nb_year in range(0, nb_years):
        year = current_year - nb_years + nb_year + 1
        security_objectives_declaration = StandardAnswer.objects.filter(
            submitter_company=company,
            sectors=sector,
            year_of_submission=year,
            status="PASS",
        )

        score_list = [0] * len(SO_SOPHISTICATION_LEVELS)

        if security_objectives_declaration.exists():
            last_declaration = security_objectives_declaration.latest("submit_date")
            aggregated_scores = (
                last_declaration.securityobjectivestatus_set.annotate(
                    level=Floor(F("score"))
                )
                .values("level")
                .annotate(count=Count("level"))
            )
            for score_data in aggregated_scores:
                index = int(score_data["level"])
                score_list[index] = score_data["count"]

        data[f"{company} {year}"] = score_list

    for nb_year in range(0, nb_years):
        year = current_year - nb_years + nb_year + 1
        latest_submit_date_per_company = (
            StandardAnswer.objects.filter(
                submitter_company=OuterRef("submitter_company"),
                sectors=sector,
                year_of_submission=year,
                # status="PASS",
            )
            .order_by("-last_update")
            .values("last_update")[:1]
        )

        latest_answers = StandardAnswer.objects.filter(
            sectors=sector,
            year_of_submission=year,
            # status="PASS",
            last_update=Subquery(latest_submit_date_per_company),
        ).distinct()
        if latest_answers.exists():
            aggregated_scores = (
                SecurityObjectiveStatus.objects.filter(
                    standard_answer__in=latest_answers
                )
                .annotate(level=Floor(F("score")))
                .values("security_objective", "level")
                .annotate(
                    avg_score=Avg("score"),
                    count=Count("level"),
                )
                .order_by("security_objective")
            )

            for score_data in aggregated_scores:
                print(
                    f"{year} ",
                    f"Security Objective: {score_data['security_objective']}, "
                    f"Level: {score_data['level']}, "
                    f"Average Score: {score_data['avg_score']}, "
                    f"Count: {score_data['count']}",
                )

    return data


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
    colors_palette = ["lightskyblue", "royalblue", "lavenderblush", "hotpink"]

    for index, (name, values) in enumerate(data.items()):
        fig.add_trace(
            go.Bar(
                x=labels,
                y=values,
                name=name,
                marker_color=colors_palette[index],
                text=values,
                textposition="outside",
            )
        )

    fig.update_layout(
        barmode="group",
        bargroupgap=0.5,
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
            y=-0.1,
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
    for name, values in data.items():
        fig.add_trace(
            go.Scatterpolar(
                r=values + [values[0]],
                theta=labels + [labels[0]],
                name=name,
                fillcolor="rgba(0,0,0,0)",
            )
        )

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
        margin=dict(l=50, r=50, t=50, b=50),
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
    charts = {
        "colorbar": generate_colorbar(),
        "security_measures_1": generate_bar_chart(
            get_data_so_average(cleaned_data), SO_SOPHISTICATION_LEVELS
        ),
        "security_measures_5a": generate_radar_chart(
            get_data_by_so_domains(), SO_DOMAINS, SO_SOPHISTICATION_LEVELS
        ),
        "security_measures_5b": generate_radar_chart(
            get_data_by_so_list(), SO_LIST, SO_SOPHISTICATION_LEVELS
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
            "years": YEARS,
            "sophistication_levels": SO_SOPHISTICATION_LEVELS,
            "so_categories": SO_DOMAINS,
            "so_list": SO_LIST,
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

    return htmldoc.write_pdf(stylesheets=stylesheets)


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

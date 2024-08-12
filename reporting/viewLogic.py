import base64
import csv
import json
import os
from io import BytesIO

import plotly.graph_objects as go
from django.conf import settings
from django.http import HttpRequest
from django.template.loader import render_to_string
from weasyprint import CSS, HTML

SO_SOPHISTICATION_LEVELS = [
    "0 (n/a)",
    "1 (basic)",
    "2 (industry standard)",
    "3 (state of the art)",
]

YEARS = [
    "2022",
    "2023",
    "2024",
]

SO_CATEGORIES = [
    "Gouvernance et gestion des risques",
    "Sécurité des ressources humaines",
    "Sécurité des systèmes et des installations",
    "Gestion de l'opération",
    "Gestion de l'incident",
    "Gestion de la continuité des activités",
    "Surveillance, audits et tests",
    "Conscience des menaces",
]


def generate_bar_chart():
    values_2019 = [1, 0, 18, 6]
    values_2020 = [0, 0, 21, 4]
    sector_avg_2019 = [1, 7, 15, 2]
    sector_avg_2020 = [1, 7, 15, 2]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=SO_SOPHISTICATION_LEVELS,
            y=values_2019,
            name="Operator (2019)",
            marker_color="lightskyblue",
            text=values_2019,
            textposition="outside",
        )
    )

    fig.add_trace(
        go.Bar(
            x=SO_SOPHISTICATION_LEVELS,
            y=values_2020,
            name="Operator (2020)",
            marker_color="royalblue",
            text=values_2020,
            textposition="outside",
        )
    )

    fig.add_trace(
        go.Bar(
            x=SO_SOPHISTICATION_LEVELS,
            y=sector_avg_2019,
            name="Moyenne du secteur (2019)",
            marker_color="lavenderblush",
            text=sector_avg_2019,
            textposition="outside",
        )
    )

    fig.add_trace(
        go.Bar(
            x=SO_SOPHISTICATION_LEVELS,
            y=sector_avg_2020,
            name="Moyenne du secteur (2020)",
            marker_color="hotpink",
            text=sector_avg_2020,
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


def generate_radar_chart():
    values_2023 = [2, 3, 2, 1, 2, 2, 2, 3, 2]
    values_2024 = [3, 3, 2, 2, 3, 3, 3, 3, 3]
    values_sector = [2, 2, 2, 2, 2, 2, 2, 2, 2]

    fig = go.Figure()

    fig.add_trace(
        go.Scatterpolar(
            r=values_2023,
            theta=SO_CATEGORIES + [SO_CATEGORIES[0]],
            name="DummyLux 2023",
            line=dict(color="orange"),
            fillcolor="rgba(0,0,0,0)",
        )
    )

    fig.add_trace(
        go.Scatterpolar(
            r=values_2024,
            theta=SO_CATEGORIES + [SO_CATEGORIES[0]],
            name="DummyLux 2024",
            line=dict(color="blue"),
            fillcolor="rgba(0,0,0,0)",
        )
    )

    fig.add_trace(
        go.Scatterpolar(
            r=values_sector,
            theta=SO_CATEGORIES + [SO_CATEGORIES[0]],
            name="Secteur",
            line=dict(color="green", dash="dash"),
            fillcolor="rgba(0,0,0,0)",
        )
    )

    fig.update_layout(
        polar=dict(
            bgcolor="white",
            gridshape="linear",
            radialaxis=dict(
                visible=True,
                range=[0, len(SO_SOPHISTICATION_LEVELS) - 1],
                showticklabels=True,
                gridcolor="lightgrey",
                gridwidth=1,
                angle=90,
                tickangle=90,
            ),
            angularaxis=dict(
                gridcolor="lightgrey",
                tickmode="array",
                showline=True,
                linewidth=1,
                linecolor="lightgrey",
            ),
        ),
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
    )

    graph = convert_graph_to_base64(fig)

    return graph


def convert_graph_to_base64(fig):
    buffer = BytesIO()
    fig.write_image(buffer, format="png")
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()

    graph = base64.b64encode(image_png)
    graph = graph.decode("utf-8")

    return graph


def parsing_risk_data_json():
    # Constants
    INPUT_FILE = "MyPrint.json"
    OUTPUT_FILE = "output.csv"
    # LANG_VALUES = {1: "fr", 2: "en", 3: "de", 4: "nl"}
    TREATMENT_VALUES = {
        1: "Reduction",
        2: "Denied",
        3: "Accepted",
        4: "Shared",
        5: "Not treated",
    }
    CSV_HEADER = [
        "service_label",
        "asset_label",
        "impact_c",
        "impact_i",
        "impact_a",
        "threat_label",
        "threat_value",
        "vulnerability_label",
        "vulnerability_value",
        "risk_c",
        "risk_i",
        "risk_a",
        "max_risk",
        "residual_risk",
        "treatment",
    ]

    with open(INPUT_FILE, encoding="utf-8") as file:
        data = json.load(file)

    csv_data = []

    def calculate_risk(impact, threat_value, vulnerability_value, factor):
        risk_value = impact * threat_value * vulnerability_value if factor else -1
        return max(risk_value, -1)

    def extract_risks(service_label, instance_data):
        instance = instance_data["instance"]
        asset_label = instance["name1"].strip()
        impact_c, impact_i, impact_a = instance["c"], instance["i"], instance["d"]

        risks = instance_data.get("risks", [])
        if risks:
            for risk in risks.values():
                threat_data = instance_data["threats"][str(risk["threat"])]
                threat_label = threat_data["label1"].strip()
                threat_value = risk["threatRate"]
                vulnerability_label = instance_data["vuls"][str(risk["vulnerability"])][
                    "label1"
                ].strip()
                vulnerability_value = risk["vulnerabilityRate"]

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
                residual_risk = risk["cacheTargetedRisk"]
                treatment = TREATMENT_VALUES.get(risk["kindOfMeasure"], "Unknown")

                csv_data.append(
                    [
                        service_label.strip(),
                        asset_label,
                        impact_c,
                        impact_i,
                        impact_a,
                        threat_label,
                        threat_value,
                        vulnerability_label,
                        vulnerability_value,
                        risk_c,
                        risk_i,
                        risk_a,
                        max_risk,
                        residual_risk,
                        treatment,
                    ]
                )

        # Process child instances recursively
        childrens = instance_data.get("children", [])
        if childrens:
            for child_data in childrens.values():
                extract_risks(service_label, child_data)

    # Extract the root instances and process them
    for instance_data in data["instances"].values():
        instance = instance_data["instance"]
        if instance["root"] == 0 and instance["parent"] == 0:
            service_label = instance["name1"]
            extract_risks(service_label, instance_data)

    # Write to CSV file
    with open(OUTPUT_FILE, "w", newline="") as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(CSV_HEADER)
        csvwriter.writerows(csv_data)

    print("CSV file created")


def get_pdf_report(request: HttpRequest):
    # Render the HTML file

    static_theme_dir = settings.STATIC_THEME_DIR
    bar_chart = generate_bar_chart()
    radar_chart = generate_radar_chart()
    output_from_parsed_template = render_to_string(
        "reporting/template.html",
        {
            "bar_chart": bar_chart,
            "radar_chart": radar_chart,
            "years": YEARS,
            "sophistication_levels": SO_SOPHISTICATION_LEVELS,
            "so_categories": SO_CATEGORIES,
            "static_theme_dir": os.path.abspath(static_theme_dir),
        },
        request=request,
    )

    htmldoc = HTML(string=output_from_parsed_template, base_url=static_theme_dir)

    stylesheets = [
        CSS(os.path.join(static_theme_dir, "css/custom.css")),
        CSS(os.path.join(static_theme_dir, "css/report.css")),
    ]

    return htmldoc.write_pdf(stylesheets=stylesheets)

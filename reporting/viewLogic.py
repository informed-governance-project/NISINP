import base64
import csv
import json
import os
import random
import textwrap
from io import BytesIO

import plotly.colors as pc
import plotly.graph_objects as go
from django.conf import settings
from django.http import HttpRequest
from django.template.loader import render_to_string
from weasyprint import CSS, HTML

SERVICES_COLOR_PALETTE = pc.DEFAULT_PLOTLY_COLORS


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

SO_COLOR_PALETTE = [
    (0, "#F8696B"),
    (0.5, "#FA9473"),
    (1, "#FCBF7B"),
    (1.5, "#FFEB84"),
    (2, "#CCDD82"),
    (2.5, "#98CE7F"),
    (3, "#63BE7B"),
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


def get_data_by_so_categories():
    data = {
        "DummyLux 2023": [random.choice(range(4)) for _ in range(len(SO_CATEGORIES))],
        "DummyLux 2024": [random.choice(range(4)) for _ in range(len(SO_CATEGORIES))],
        "Secteur": [random.choice(range(4)) for _ in range(len(SO_CATEGORIES))],
    }

    return data


def get_data_by_so_list():
    data = {
        "DummyLux 2023": [random.choice(range(4)) for _ in range(len(SO_LIST))],
        "DummyLux 2024": [random.choice(range(4)) for _ in range(len(SO_LIST))],
    }

    return data


def get_data_so_average():
    data = {
        "Operator 2019": [1, 0, 18, 6],
        "Operator 2020": [0, 0, 21, 4],
        "Sector Avg 2019": [1, 7, 15, 2],
        "Sector Avg 2020": [1, 7, 15, 2],
    }

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


def generate_radar_chart(data, labels):
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
                range=[0, len(SO_SOPHISTICATION_LEVELS) - 1],
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
    static_dir = settings.STATIC_ROOT
    charts = {
        "colorbar": generate_colorbar(),
        "security_measures_1": generate_bar_chart(
            get_data_so_average(), SO_SOPHISTICATION_LEVELS
        ),
        "security_measures_5a": generate_radar_chart(
            get_data_by_so_categories(), SO_CATEGORIES
        ),
        "security_measures_5b": generate_radar_chart(get_data_by_so_list(), SO_LIST),
        "risks_1": generate_bar_chart(get_data_risks_average(), OPERATOR_SERVICES),
        "risks_3": generate_bar_chart(get_data_high_risks_average(), OPERATOR_SERVICES),
        "risks_4": generate_bar_chart(
            get_data_evolution_highest_risks(), ["Ra1", "Ra2", "Ra3", "Ra4", "Ra5"]
        ),
    }

    output_from_parsed_template = render_to_string(
        "reporting/template.html",
        {
            "charts": charts,
            "years": YEARS,
            "sophistication_levels": SO_SOPHISTICATION_LEVELS,
            "so_categories": SO_CATEGORIES,
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

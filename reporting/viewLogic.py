import base64
import csv
import json
from io import BytesIO

import plotly.graph_objects as go


def generate_bar_chart():
    # Data
    categories = [
        "0 (n/a)",
        "1 (basic)",
        "2 (industry standard)",
        "3 (state of the art)",
    ]
    values_2019 = [1, 0, 18, 6]
    values_2020 = [0, 0, 21, 4]
    sector_avg_2019 = [1, 7, 15, 2]
    sector_avg_2020 = [1, 7, 15, 2]

    # Create traces with text on bars
    trace_2019 = go.Bar(
        x=categories,
        y=values_2019,
        name="Operator (2019)",
        marker_color="lightskyblue",
        text=values_2019,
        textposition="outside",
    )

    trace_2020 = go.Bar(
        x=categories,
        y=values_2020,
        name="Operator (2020)",
        marker_color="royalblue",
        text=values_2020,
        textposition="outside",
    )

    trace_sector_2019 = go.Bar(
        x=categories,
        y=sector_avg_2019,
        name="Moyenne du secteur (2019)",
        marker_color="lavenderblush",
        text=sector_avg_2019,
        textposition="outside",
    )

    trace_sector_2020 = go.Bar(
        x=categories,
        y=sector_avg_2020,
        name="Moyenne du secteur (2020)",
        marker_color="hotpink",
        text=sector_avg_2020,
        textposition="outside",
    )

    # Combine the traces
    data = [trace_2019, trace_sector_2019, trace_2020, trace_sector_2020]

    # Layout
    layout = go.Layout(
        barmode="group",
        bargroupgap=0.5,
        xaxis=dict(
            showline=True,  # Show x-axis line
            showgrid=False,  # Hide x-axis grid lines
            zeroline=True,  # Hide x-axis zero line
            linecolor="black",  # Color of the axis
        ),
        yaxis=dict(
            showline=True,  # Show y-axis line
            showgrid=True,  # Hide y-axis grid lines
            zeroline=False,  # Hide y-axis zero line
            gridcolor="lightgray",
            linecolor="black",  # Color of the axis line
        ),
        plot_bgcolor="rgba(0,0,0,0)",  # Transparent plot area background
        showlegend=True,
        legend=dict(
            orientation="h",  # Horizontal legend
            x=0.5,  # Center legend horizontally
            y=-0.1,  # Position below the chart
            xanchor="center",  # Align legend by its center
            yanchor="top",  # Align legend by the top of its box
            traceorder="normal",  # Order of traces in the legend
            itemwidth=50,  # Width allocated to each item
            valign="middle",  # Aligns items vertically in the middle
            title_font_size=16,  # Font size of the legend title
        ),
        margin=dict(t=10, b=50),
    )

    fig = go.Figure(data=data, layout=layout)

    # Save the chart to a BytesIO object
    buffer = BytesIO()
    fig.write_image(buffer, format="png")
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()

    # Encode the image to base64
    graph = base64.b64encode(image_png)
    graph = graph.decode("utf-8")

    return graph


def parsing_risk_data_json():
    # Constants
    INPUT_FILE = "MyPrint.json"
    OUTPUT_FILE = "output.csv"
    LANG_VALUES = {1: "fr", 2: "en", 3: "de", 4: "nl"}
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

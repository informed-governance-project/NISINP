import base64
import datetime
import os
import shutil
import uuid
import zipfile
from io import BytesIO
from pathlib import Path

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import formats
from django.utils.translation import activate
from docx import Document
from docx.shared import Mm
from docxtpl import DocxTemplate, InlineImage, RichTextParagraph

from .globals import TRANSLATIONS_CONTEXT
from .helpers import (
    convert_docx_to_pdf,
    create_entry_log,
    fix_outer_column_borders,
    get_charts,
    get_risk_data,
    get_so_data,
    merge_subdoc_into_placeholder,
    redistribute_column_widths_proportional,
)
from .models import CompanyReporting, Configuration, GeneratedReport, Template


@shared_task
def generate_data(cleaned_data):
    activate(cleaned_data.get("language", "en"))
    report_configuration_id = cleaned_data["report_configuration_id"]
    colors = Configuration.objects.get(pk=report_configuration_id).colors.values_list(
        "color"
    )
    template_id = cleaned_data["template_id"]
    so_data = get_so_data(cleaned_data)
    risk_data = get_risk_data(cleaned_data)
    charts = get_charts(so_data, risk_data, colors)

    data = {
        "company": cleaned_data["company"]["name"],
        "year": cleaned_data["year"],
        "sector": cleaned_data["sector"]["name"],
        "threshold_for_high_risk": cleaned_data["threshold_for_high_risk"],
        "top_ranking": cleaned_data["top_ranking"],
        "report_recommendations": cleaned_data["report_recommendations"],
        "charts": charts,
        "so_data": so_data,
        "risk_data": risk_data,
        "nb_years": cleaned_data["nb_years"],
        "company_reporting": cleaned_data["company_reporting"],
        "translations": TRANSLATIONS_CONTEXT,
        "template_id": template_id,
    }

    return data


@shared_task
def generate_docx_task(data):
    tmp_dir = Path(settings.PATH_FOR_REPORTING_PDF)
    subdocs_templates_dir = Path(
        os.path.join(settings.BASE_DIR, "reporting", "subdocs_templates")
    )
    tmp_dir.mkdir(exist_ok=True)
    main_docx_path = Path(tmp_dir / "main_doc.docx")
    template_id = data["template_id"]
    template_file = Template.objects.get(pk=template_id).template_file
    template_path = BytesIO(bytes(template_file))
    tmp_output_path = tmp_dir / "tmp_doc.docx"
    rendered_subs_docs = {}
    document_charts = {
        "chart_average_risk_level": {
            "width": Mm(140),
        },
        "chart_high_risk_rate": {
            "width": Mm(140),
        },
        "chart_average_high_risk_level": {
            "width": Mm(140),
        },
        "chart_evolution_highest_risks": {
            "width": Mm(140),
        },
    }
    document_tables = {
        "table_of_evolution_security_objectives": {
            "context": {
                "table": data["so_data"]["company_so_by_year"],
                "years": data["so_data"]["years"],
                "year": data["year"],
            },
            "column_proportions": [0.4]
            + [0.1] * len(data["so_data"]["years"])
            + [0.15],
        },
        "table_of_evolution_security_objectives_by_domain": {
            "context": {
                "table": data["so_data"]["company_so_by_domain"],
                "years": data["so_data"]["years"],
                "year": data["year"],
            },
            "column_proportions": [0.4]
            + [0.1] * len(data["so_data"]["years"])
            + [0.15] * 2,
        },
        "table_of_highest_security_objectives_in_the_sector": {
            "context": {
                "table": data["so_data"]["sector_so_by_year_desc"][str(data["year"])],
                "year": data["year"],
            },
            "column_proportions": [0.05] + [0.65] + [0.15] * 2,
        },
        "table_of_lowest_security_objectives_in_the_sector": {
            "context": {
                "table": data["so_data"]["sector_so_by_year_asc"][str(data["year"])],
                "year": data["year"],
            },
            "column_proportions": [0.05] + [0.65] + [0.15] * 2,
        },
        "table_of_evolution_of_the_weakest_security_objectives": {
            "context": {
                "table": data["so_data"]["company_so_by_priority"],
                "years": data["so_data"]["years"],
            },
            "column_proportions": [0.4]
            + [0.15] * len(data["so_data"]["years"])
            + [0.15],
        },
        "table_of_security_objectives_by_maturity_level": {
            "context": {
                "table": data["so_data"]["company_so_by_level"],
            },
            "column_proportions": [0.25]
            * len(data["so_data"]["company_so_by_level"]["headers"]),
        },
        "maturity_level_legend": {
            "context": {
                "maturity_levels": data["so_data"]["maturity_levels"],
            },
        },
        "table_of_evolution_of_the_highest_risks": {
            "context": {
                "table": data["risk_data"]["data_risks_top_ranking"],
                "years": data["risk_data"]["years"],
            },
            "column_proportions": [0.1, 0.25, 0.25, 0.3]
            + [0.1] * len(data["risk_data"]["years"]),
        },
        "table_of_treatment_of_the_highest_risks": {
            "context": {
                "table": data["risk_data"]["data_risks_top_ranking"],
            },
            "column_proportions": [0.08, 0.18, 0.18, 0.25, 0.13, 0.17, 0.13],
        },
        "table_of_risk_summary": {
            "context": {
                "table": data["risk_data"]["risks_stats_by_year"],
                "years": data["risk_data"]["years"],
            },
            "column_proportions": [0.7] + [0.15] * len(data["risk_data"]["years"]),
            "table_width_dxa": 7380,  # 13cm
        },
        "table_of_top_threats_by_occurrence": {
            "context": {
                "table": data["risk_data"]["top_threats"],
            },
            "column_proportions": [0.1, 0.9],
            "table_width_dxa": 8504,  # 15cm
        },
        "table_of_top_vulnerabilities_by_occurrence": {
            "context": {
                "table": data["risk_data"]["top_vulnerabilities"],
            },
            "column_proportions": [0.1, 0.9],
            "table_width_dxa": 8504,  # 15cm
        },
        "table_of_recommendations": {
            "context": {
                "table": data["risk_data"]["recommendations_evolution"],
            },
            "column_proportions": [0.7, 0.15, 0.15],
        },
    }

    main_doc_template = DocxTemplate(template_path)
    main_doc = Document(template_path)

    report_recommendations = RichTextParagraph()
    for rec in data["report_recommendations"]:
        report_recommendations.add(rec, parastyle="CircleBullet")

    context = {
        "operator_name": data["company"],
        "sector": data["sector"],
        "year": data["year"],
        "threshold_for_high_risk": data["threshold_for_high_risk"],
        "top_ranking": data["top_ranking"],
        "report_recommendations": report_recommendations,
        "report_observations": data["company_reporting"]["comment"],
        "publication_date": formats.date_format(datetime.date.today(), format="d F Y"),
    }
    for chart_name, chart_data in data["charts"].items():
        chart_bytes = BytesIO(base64.b64decode(chart_data))
        chart_with = document_charts.get(chart_name, {}).get("width", Mm(170))
        context[chart_name] = InlineImage(
            main_doc_template, chart_bytes, width=chart_with
        )

    for table_name, table_info in document_tables.items():
        sub_template_path = subdocs_templates_dir / f"{table_name}_template.docx"
        sub_rendered_path = tmp_dir / f"{table_name}_rendered.docx"
        context[table_name] = str(table_name)
        table_info["context"]["translations"] = data["translations"]
        sub_doc_template = DocxTemplate(sub_template_path)
        sub_doc_template.render(table_info["context"])
        sub_doc_template.save(sub_rendered_path)
        sub_doc = Document(sub_rendered_path)
        for table in sub_doc.tables:
            table_width_dxa = None
            if "table_width_dxa" in table_info:
                # 1dxa = 1cm * 28.346 * 20
                table_width_dxa = table_info["table_width_dxa"]
            if "column_proportions" in table_info:
                redistribute_column_widths_proportional(
                    table, table_info["column_proportions"], main_doc, table_width_dxa
                )
            fix_outer_column_borders(table._element)
        sub_doc.save(sub_rendered_path)
        rendered_subs_docs[table_name] = sub_rendered_path

    main_doc_template.render(context)
    main_doc_template.save(main_docx_path)
    current_doc = main_docx_path

    for placeholder, sub_rendered_path in rendered_subs_docs.items():
        sub_rendered_path = Path(sub_rendered_path)
        try:
            merge_subdoc_into_placeholder(
                main_docx_path=current_doc,
                subdoc_path=sub_rendered_path,
                placeholder=placeholder,
                output_path=tmp_output_path,
            )
            current_doc = tmp_output_path
        finally:
            if sub_rendered_path.exists():
                sub_rendered_path.unlink(missing_ok=True)

    main_docx_path.unlink(missing_ok=True)
    return str(current_doc)


@shared_task
def generate_pdf_task(docx_path):
    docx_path = Path(docx_path)

    try:
        pdf_path = convert_docx_to_pdf(str(docx_path))
        return str(pdf_path)

    finally:
        if docx_path.exists():
            docx_path.unlink(missing_ok=True)


@shared_task
def save_file_task(
    temp_file_path, run_id, user_id, company_reporting_id, filename, is_multiple_files
):
    file_uuid = uuid.uuid4()
    User = get_user_model()
    user = User.objects.get(id=user_id)
    output_dir = os.path.join(settings.PATH_FOR_REPORTING_PDF, str(user.id))
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, str(file_uuid))

    if is_multiple_files:
        temp_output_dir = os.path.join(output_dir, run_id)
        os.makedirs(temp_output_dir, exist_ok=True)
        file_path = os.path.join(temp_output_dir, filename)
    else:
        GeneratedReport.objects.create(
            user=user,
            file_uuid=file_uuid,
            filename=filename,
        )

    shutil.move(temp_file_path, file_path)
    company_reporting = CompanyReporting.objects.get(id=company_reporting_id)
    create_entry_log(user, company_reporting, "GENERATE REPORT")

    return file_path


@shared_task
def zip_files_task(file_paths, user_id, error_messages):
    file_uuid = uuid.uuid4()
    User = get_user_model()
    user = User.objects.get(id=user_id)
    output_dir = os.path.join(settings.PATH_FOR_REPORTING_PDF, str(user.id))
    zip_filename = f"reports_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    zip_path = os.path.join(output_dir, str(file_uuid))

    if not isinstance(file_paths, list):
        file_paths = [file_paths]

    with zipfile.ZipFile(zip_path, "w") as zipf:
        for file_path in file_paths:
            if os.path.exists(file_path):
                arcname = os.path.basename(file_path)
                zipf.write(file_path, arcname=arcname)
            else:
                print(f"File not found: {file_path}")

        if error_messages:
            error_log = "\n".join(error_messages)
            zipf.writestr("error_log.txt", error_log)

    temp_dir = os.path.dirname(file_paths[0])

    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

    GeneratedReport.objects.create(
        user=user,
        file_uuid=file_uuid,
        filename=zip_filename,
    )

    return zip_path

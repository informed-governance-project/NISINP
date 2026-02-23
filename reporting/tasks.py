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
from docx import Document
from docx.shared import Mm
from docxtpl import DocxTemplate, InlineImage

from .globals import SO_COLOR_PALETTE
from .helpers import (
    convert_docx_to_pdf,
    create_entry_log,
    get_charts,
    get_gradient_color,
    get_risk_data,
    get_so_data,
    merge_subdoc_into_placeholder,
    redistribute_column_widths_proportional,
)
from .models import CompanyReporting, GeneratedReport


@shared_task
def generate_data(cleaned_data):
    so_data = get_so_data(cleaned_data)
    risk_data = get_risk_data(cleaned_data)
    charts = get_charts(so_data, risk_data)

    data = {
        "company": cleaned_data["company"]["name"],
        "year": cleaned_data["year"],
        "sector": cleaned_data["sector"]["name"],
        "top_ranking": cleaned_data["top_ranking"],
        "report_recommendations": cleaned_data["report_recommendations"],
        "charts": charts,
        "so_data": so_data,
        "risk_data": risk_data,
        "nb_years": cleaned_data["nb_years"],
        "company_reporting": cleaned_data["company_reporting"],
        "translations": cleaned_data["translations"],
    }

    return data


@shared_task
def generate_docx_task(data):
    tmp_dir = Path(settings.PATH_FOR_REPORTING_PDF)
    tmp_dir.mkdir(exist_ok=True)
    generated_docx_path = Path(tmp_dir / "generated_doc.docx")
    template_path = tmp_dir / "template_fr.docx"
    merged_path = tmp_dir / "merged.docx"
    rendered_subs_docs = {}
    document_tables = {
        "table_of_evolution_security_objectives_by_domain": {
            "context": {
                "table": convert_so_data_for_docxtpl(data["so_data"]),
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
        },
        "table_of_lowest_security_objectives_in_the_sector": {
            "context": {
                "table": data["so_data"]["sector_so_by_year_asc"][str(data["year"])],
                "year": data["year"],
            },
        },
        "maturity_level_legend": {
            "context": {
                "maturity_levels": get_maturity_level_context(
                    data["so_data"]["maturity_levels"]
                ),
            },
        },
    }

    doc = DocxTemplate(template_path)
    context = {
        "operator_name": data["company"],
        "sector": data["sector"],
        "year": data["year"],
        "so_data": data["so_data"],
    }
    for chart_name, chart_data in data["charts"].items():
        chart_bytes = BytesIO(base64.b64decode(chart_data))
        context[chart_name] = InlineImage(doc, chart_bytes, width=Mm(170))

    for table_name, table_info in document_tables.items():
        sub_template_path = tmp_dir / f"{table_name}_template.docx"
        sub_rendered_path = tmp_dir / f"{table_name}_rendered.docx"
        context[table_name] = str(table_name)
        table_info["context"]["translations"] = data["translations"]
        sub = DocxTemplate(sub_template_path)
        sub.render(table_info["context"])
        sub.save(sub_rendered_path)
        if "column_proportions" in table_info:
            main_doc = Document(template_path)
            template = Document(sub_rendered_path)
            for table in template.tables:
                redistribute_column_widths_proportional(
                    table, table_info["column_proportions"], main_doc
                )
            template.save(sub_rendered_path)
        rendered_subs_docs[table_name] = sub_rendered_path

    doc.render(context)
    doc.save(generated_docx_path)
    current_doc = generated_docx_path

    for placeholder, sub_rendered_path in rendered_subs_docs.items():
        sub_rendered_path = Path(sub_rendered_path)
        try:
            merge_subdoc_into_placeholder(
                main_docx_path=current_doc,
                subdoc_path=sub_rendered_path,
                placeholder=placeholder,
                output_path=merged_path,
            )
            current_doc = merged_path
        finally:
            if sub_rendered_path.exists():
                sub_rendered_path.unlink(missing_ok=True)

    generated_docx_path.unlink(missing_ok=True)
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


def convert_so_data_for_docxtpl(so_data):
    years = sorted(so_data["years"])
    data = []

    for domain, data_by_year in so_data["company_so_by_domain"].items():
        scores = []
        evolutions = []
        last_avgs = []

        for year_index, year in enumerate(years):
            year_data = data_by_year.get(str(year), {})
            value = round(year_data.get("score") or 0, 1)
            is_last = year_index == len(years) - 1
            score = {
                "value": value,
                "color": get_gradient_color(value) if is_last else "#FFFFFF",
            }
            evo = year_data.get("evolution")
            sector_avg = round(year_data.get("sector_avg") or 0, 1)

            scores.append(score)
            evolutions.append(evo)
            last_avgs.append(sector_avg)

        data.append(
            {
                "domain": domain,
                "years": scores,
                "evolution": evolutions,
                "last_avg": last_avgs,
            }
        )

    return {"years": years, "data": data}


def get_maturity_level_context(maturity_levels):
    context = []
    for index, maturity_level in enumerate(maturity_levels):
        data = {
            "index": index,
            "color": SO_COLOR_PALETTE[index][1],
            "label": maturity_level,
        }
        context.append(data)

    return context

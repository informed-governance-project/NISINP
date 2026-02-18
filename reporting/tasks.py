import datetime
import logging
import os
import shutil
import uuid
import zipfile
from io import BytesIO
from pathlib import Path

import plotly.colors as pc
from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from docx.shared import Mm
from docxtpl import DocxTemplate, InlineImage
from weasyprint import CSS, HTML

from .helpers import (
    convert_docx_to_pdf,
    create_entry_log,
    get_charts,
    get_risk_data,
    get_so_data,
)
from .models import CompanyReporting, GeneratedReport

# Increasing weasyprint log level
for logger_name in ["weasyprint", "fontTools", "fontTools.subset"]:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.ERROR)


@shared_task
def generate_pdf_data(cleaned_data):
    bootstrap_icons_dir = os.path.join(
        settings.STATIC_DIR, "npm_components/bootstrap-icons"
    )
    so_data = get_so_data(cleaned_data)
    risk_data = get_risk_data(cleaned_data)
    charts = get_charts(so_data, risk_data)

    rendered_data = render_to_string(
        "report/reporting/template.html",
        {
            "company": cleaned_data["company"],
            "year": cleaned_data["year"],
            "sector": cleaned_data["sector"],
            "top_ranking": cleaned_data["top_ranking"],
            "report_recommendations": cleaned_data["report_recommendations"],
            "charts": charts,
            "so_data": so_data,
            "risk_data": risk_data,
            "nb_years": cleaned_data["nb_years"],
            "service_color_palette": pc.DEFAULT_PLOTLY_COLORS,
            "bootstrap_icons_dir": os.path.abspath(bootstrap_icons_dir),
            "company_reporting": cleaned_data["company_reporting"],
        },
    )

    tmp_dir = Path("tmp")
    tmp_dir.mkdir(exist_ok=True)
    generated_docx_path = tmp_dir / "generated_doc.docx"
    template_path = tmp_dir / "template_fr.docx"
    doc = DocxTemplate(template_path)
    context = {
        "operator_name": cleaned_data["company"]["name"],
        "sector": cleaned_data["sector"]["name"],
        "year": cleaned_data["year"],
        "chart_1": InlineImage(doc, charts["security_measures_1"], width=Mm(160)),
        "so_data": so_data,
        "table": convert_so_data_for_docxtpl(so_data),
    }
    doc.render(context)
    doc.save(generated_docx_path)
    convert_docx_to_pdf(str(generated_docx_path))
    return rendered_data


@shared_task
def generate_pdf_task(data, css_paths):
    static_theme_dir = settings.STATIC_THEME_DIR
    stylesheets = [CSS(path) for path in css_paths]
    pdf_buffer = BytesIO()
    HTML(string=data, base_url=static_theme_dir).write_pdf(
        pdf_buffer, stylesheets=stylesheets, pdf_variant="pdf/ua-1"
    )
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()


@shared_task
def save_pdf_task(
    pdf_bytes, run_id, user_id, company_reporting_id, filename, is_multiple_files
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

    with open(file_path, "wb") as f:
        f.write(pdf_bytes)

    company_reporting = CompanyReporting.objects.get(id=company_reporting_id)
    create_entry_log(user, company_reporting, "GENERATE REPORT")

    return file_path


@shared_task
def zip_pdfs_task(file_paths, user_id, error_messages):
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
    # Sort years
    years = sorted(so_data["years"])
    data = []

    for domain, data_by_year in so_data["company_so_by_domain"].items():
        scores = []
        evolutions = []
        last_avgs = []

        for year in years:
            year_data = data_by_year.get(year, {})
            score = float(year_data.get("score") or 0)
            evo = year_data.get("evolution")
            sector_avg = float(year_data.get("sector_avg") or 0)

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

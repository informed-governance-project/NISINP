import datetime
import logging
import os
import shutil
import uuid
import zipfile
from io import BytesIO

import plotly.colors as pc
from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from weasyprint import CSS, HTML

from .helpers import create_entry_log, get_charts, get_risk_data, get_so_data
from .models import CompanyReporting, GeneratedReport

# Increasing weasyprint log level
for logger_name in ["weasyprint", "fontTools"]:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.ERROR)


@shared_task
def generate_pdf_data(cleaned_data):
    static_theme_dir = settings.STATIC_THEME_DIR
    bootstrap_icons_dir = os.path.join(
        settings.STATIC_DIR, "npm_components/bootstrap-icons"
    )

    so_data = get_so_data(cleaned_data)
    risk_data = get_risk_data(cleaned_data)
    charts = get_charts(so_data, risk_data)

    rendered_data = render_to_string(
        "reporting/template.html",
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
            "static_theme_dir": os.path.abspath(static_theme_dir),
            "bootstrap_icons_dir": os.path.abspath(bootstrap_icons_dir),
            "company_reporting": cleaned_data["company_reporting"],
        },
    )
    return rendered_data


@shared_task
def generate_pdf_task(data, css_paths):
    stylesheets = [CSS(path) for path in css_paths]
    pdf_buffer = BytesIO()
    HTML(string=data).write_pdf(pdf_buffer, stylesheets=stylesheets)
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

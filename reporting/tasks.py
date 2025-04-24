import datetime
import os
import shutil
import uuid
import zipfile
from io import BytesIO

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from weasyprint import CSS, HTML

from .helpers import create_entry_log
from .models import CompanyReporting, GeneratedReport


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

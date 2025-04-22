import uuid
from governanceplatform.settings import PATH_FOR_REPORTING_PDF
from django.contrib.auth import get_user_model
from celery import shared_task
from weasyprint import HTML, CSS
# from io import BytesIO
import logging

from .models import GeneratedReport

logger = logging.getLogger(__name__)


@shared_task
def generate_pdf_task(data, css_paths, filename, user_id):

    User = get_user_model()
    user = User.objects.get(pk=user_id)
    uuid_path = uuid.uuid4()
    pdf_file = f"{PATH_FOR_REPORTING_PDF}{uuid_path}.pdf"
    stylesheets = [CSS(path) for path in css_paths]

    htmldoc = HTML(string=data)

    # pdf_buffer = BytesIO()
    htmldoc.write_pdf(target=pdf_file, stylesheets=stylesheets)
    # htmldoc.write_pdf(pdf_buffer, stylesheets=stylesheets)
    # pdf_buffer.seek(0)
    GeneratedReport.objects.create(
        user=user,
        file_uuid=uuid_path,
        filename=filename,
    )

    return "pdf_buffer"


# test task to test the installation
@shared_task
def test_task():
    print("Task is running!")
    return "task success"

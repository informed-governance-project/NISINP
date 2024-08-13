from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.translation import gettext_lazy as _

from reporting.viewLogic import get_pdf_report


@login_required
def report_generation(request):
    try:
        pdf_report = get_pdf_report(request)
    except Exception:
        messages.warning(request, _("An error occurred while generating the report."))
        return HttpResponseRedirect("/incidents")

    response = HttpResponse(pdf_report, content_type="application/pdf")
    response["Content-Disposition"] = "attachment;filename=annual_report.pdf"

    return response

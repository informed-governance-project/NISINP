from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from django.shortcuts import render
from django_otp.decorators import otp_required
from .forms import RiskAnalysisSubmissionForm
import json

from reporting.viewLogic import get_pdf_report

from governanceplatform.helpers import (
    get_active_company_from_session,
)


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


# To DO : restrict acces to incidentuser
@login_required
@otp_required
def risk_analysis_submission(request):
    if request.method == 'POST':
        updated_data = request.POST.copy()
        # TO DO : PARSE CORRECTLY THE JSON to avoid other fileformat and unsecure file
        f = json.loads(request.FILES['JSON_file'].read())
        updated_data.update({'data': f})
        form = RiskAnalysisSubmissionForm(updated_data, request.FILES)
        if form.is_valid():
            anr = form.save(commit=False)
            # TO DO : manage the multiple company stuff
            anr.company = get_active_company_from_session(request)
            anr.save()

        else:
            print('nonvalide')
            print(form.errors)
    else:
        form = RiskAnalysisSubmissionForm()

    return render(request, "operator/reporting/risk_analysis_submission.html", {'form': form})

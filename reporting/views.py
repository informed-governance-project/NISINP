from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_otp.decorators import otp_required

# from governanceplatform.helpers import get_active_company_from_session
from reporting.viewLogic import (  # parsing_risk_data_json,
    get_pdf_report,
    validate_json_file,
)

from .forms import RiskAnalysisSubmissionForm


@login_required
@otp_required
def reporting(request):
    return render(request, "home/base.html")


@login_required
@otp_required
def report_generation(request):
    try:
        pdf_report = get_pdf_report(request)
    except Exception:
        messages.warning(request, _("An error occurred while generating the report."))
        return HttpResponseRedirect(reverse("incidents"))

    response = HttpResponse(pdf_report, content_type="application/pdf")
    response["Content-Disposition"] = "attachment;filename=annual_report.pdf"

    return response


# To DO : restrict acces to incidentuser
# @login_required
# @otp_required
# def risk_analysis_submission(request):
#     if request.method == "POST":
#         json_file = request.FILES["data"]
#         try:
#             request.FILES["data"] = validate_json_file(json_file)
#         except ValidationError as e:
#             messages.error(request, f"Error: {str(e)}")
#             return HttpResponseRedirect(reverse("risk_analysis_submission"))

#         form = RiskAnalysisSubmissionForm(request.POST, request.FILES)
#         if form.is_valid():
#             risk_analysis = form.save(commit=False)
#             # TO DO : manage the multiple company stuff
#             risk_analysis.company = get_active_company_from_session(request)
#             risk_analysis.save()

#             parsing_risk_data_json(risk_analysis)

#             messages.success(request, _("Risk Analysis submitted successfully"))

#     form = RiskAnalysisSubmissionForm()

#     return render(
#         request, "operator/reporting/risk_analysis_submission.html", {"form": form}
#     )


@login_required
@otp_required
def risk_analysis_submission(request):
    form = RiskAnalysisSubmissionForm(request.POST, request.FILES)
    if request.method == "POST":
        files = request.FILES.getlist("files")
        file_messages = {"success": [], "error": []}
        for file in files:
            try:
                validate_json_file(file)
                print(file.name)
                file_messages["success"].append(
                    f"{file.name}: Risk Analysis submitted successfully"
                )
            except ValidationError as e:
                file_messages["error"].append(f"{file.name}: {str(e)}")

        for message in file_messages["success"]:
            messages.success(request, message)
        for message in file_messages["error"]:
            messages.error(request, message)

    return render(
        request, "operator/reporting/risk_analysis_submission.html", {"form": form}
    )

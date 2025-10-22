import csv
import re
from collections import OrderedDict
from datetime import date
from urllib.parse import urlencode, urlparse

import pytz
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods
from django_countries import countries
from django_otp.decorators import otp_required
from formtools.wizard.views import SessionWizardView

from governanceplatform.helpers import (
    can_access_incident,
    can_create_incident_report,
    can_edit_incident_report,
    get_active_company_from_session,
    is_observer_user,
    is_user_operator,
    is_user_regulator,
    user_in_group,
)
from governanceplatform.models import CompanyUser, RegulatorUser, Sector
from governanceplatform.settings import (
    MAX_PRELIMINARY_NOTIFICATION_PER_DAY_PER_USER,
    PUBLIC_URL,
    SITE_NAME,
    TIME_ZONE,
)

from .decorators import check_user_is_correct, regulator_role_required
from .email import send_email
from .filters import IncidentFilter
from .forms import ContactForm, IncidentStatusForm, get_forms_list
from .globals import REGIONAL_AREA, REPORT_STATUS_MAP, WORKFLOW_REVIEW_STATUS
from .helpers import get_workflow_categories, is_deadline_exceeded
from .models import (
    Answer,
    Impact,
    Incident,
    IncidentWorkflow,
    LogReportRead,
    PredefinedAnswer,
    QuestionOptions,
    ReportTimeline,
    SectorRegulation,
    SectorRegulationWorkflow,
    Workflow,
)
from .pdf_generation import get_pdf_report


@login_required
@otp_required
@check_user_is_correct
def get_incidents(request):
    """Returns the list of incidents depending on the account type."""
    user = request.user
    incidents = Incident.objects.filter(sector_regulation__isnull=False).order_by(
        "-incident_notification_date"
    )
    html_view = "operator/incidents.html"

    search_value = request.GET.get("search", None)

    if "reset" in request.GET or search_value == "":
        request.session.pop("incidents_filter_params", None)
        return redirect("incidents")

    # Save filter params in user's session
    current_params = request.session.get("incidents_filter_params", {}).copy()

    for key, values in request.GET.lists():
        current_params[key] = values if key == "affected_sectors" else values[0]

    incidents_filter_params = current_params
    request.session["incidents_filter_params"] = incidents_filter_params

    if is_user_regulator(user):
        html_view = "regulator/incidents.html"
        request.session["is_regulator_incidents"] = False
        if request.path == reverse("regulator_incidents"):
            html_view = "operator/incidents.html"
            # Filter regulator incidents
            incidents = incidents.filter(regulator=user.regulators.first())
            request.session["is_regulator_incidents"] = True
        elif user_in_group(user, "RegulatorUser"):
            # RegulatorUser has access to all incidents linked by sectors.
            incidents = incidents.filter(
                affected_sectors__in=request.user.get_sectors().all()
            ).distinct()

        else:
            # Filter incidents by regulator
            incidents = incidents.filter(
                sector_regulation__regulator__in=user.regulators.all()
            )
    elif is_observer_user(user):
        html_view = "observer/incidents.html"
        incidents = (
            user.observers.first()
            .get_incidents()
            .order_by("-incident_notification_date")
        )
        f = IncidentFilter(incidents_filter_params, queryset=incidents.order_by("id"))
    elif user_in_group(user, "OperatorAdmin") or user_in_group(user, "OperatorUser"):
        # OperatorAdmin can see all the reports of the selected company.
        incidents = incidents.filter(company__id=request.session.get("company_in_use"))
        f = IncidentFilter(incidents_filter_params, queryset=incidents)
    else:
        # OperatorUser and IncidentUser can see only their reports.
        incidents = incidents.filter(contact_user=user)

    f = IncidentFilter(incidents_filter_params, queryset=incidents)
    incident_list = f.qs

    per_page = incidents_filter_params.get("per_page", 10)
    page_number = incidents_filter_params.get("page")
    paginator = Paginator(incident_list, per_page)
    page_obj = paginator.get_page(page_number)

    for incident in page_obj.object_list:
        incident.all_reports = []
        completed_workflows = incident.get_workflows_completed()
        all_workflows = incident.get_all_workflows()
        completed_workflow_ids = [wf.workflow.id for wf in completed_workflows]
        all_workflow_ids = [wf.id for wf in all_workflows]

        incident.formsStatus = IncidentStatusForm(
            instance=incident,
        )

        for idx, report in enumerate(all_workflows):
            latest = incident.get_latest_incident_workflow_by_workflow(report)
            latest_id = latest.id if latest else None
            report_id = report.id
            latest_incident_workflow = None

            latest_incident_workflow = next(
                (
                    iw
                    for iw in completed_workflows
                    if iw.workflow.id == report.id
                    and (latest_id is None or iw.id == latest_id)
                ),
                None,
            )

            status = (
                latest_incident_workflow.review_status
                if latest_incident_workflow
                else is_deadline_exceeded(
                    report,
                    incident,
                )
            )

            mapping = REPORT_STATUS_MAP.get(status, REPORT_STATUS_MAP["UNDE"])

            is_disabled = False

            if html_view == "operator/incidents.html":
                if incident.incident_status == "CLOSE":
                    is_disabled = True
                if not completed_workflows and idx != 0:
                    is_disabled = True
                elif (
                    idx < len(all_workflow_ids) - 1
                    and all_workflow_ids[idx + 1] in completed_workflow_ids
                ):
                    is_disabled = True
                elif (
                    idx < len(all_workflow_ids) - 1
                    and idx > 1
                    and all_workflow_ids[idx - 1] not in completed_workflow_ids
                ):
                    is_disabled = True
                elif (
                    len(all_workflow_ids) > 1
                    and idx == len(all_workflow_ids) - 1
                    and all_workflow_ids[idx - 1] not in completed_workflow_ids
                ):
                    is_disabled = True

            incident.all_reports.append(
                {
                    "id": report_id,
                    "name": str(report),
                    "latest_incident_workflow": latest_incident_workflow,
                    "css_class": mapping["class"],
                    "tooltip": mapping["tooltip"],
                    "is_disabled": is_disabled,
                }
            )

    is_filtered = {
        k: v
        for k, v in incidents_filter_params.items()
        if k not in ["page", "per_page"]
    }

    return render(
        request,
        html_view,
        context={
            "site_name": SITE_NAME,
            "filter": f,
            "incidents": page_obj,
            "is_filtered": bool(is_filtered),
            "is_regulator_incidents": request.session.get(
                "is_regulator_incidents", False
            ),
        },
    )


@login_required
@otp_required
@check_user_is_correct
def get_form_list(request, form_list=None):
    if is_incidents_report_limit_reached(request):
        return HttpResponseRedirect("/incidents")
    """Initialize data for the preliminary notification."""
    if form_list is None:
        form_list = get_forms_list()
    return FormWizardView.as_view(
        form_list,
        initial_dict={"0": ContactForm.prepare_initial_value(request=request)},
        condition_dict={
            "3": lambda wizard: show_form_condition(wizard).get("has_sector", False),
            "4": lambda wizard: show_form_condition(wizard).get(
                "detection_date_needed", False
            ),
        },
    )(request)


@login_required
@otp_required
@check_user_is_correct
def create_workflow(request):
    incident_id = request.GET.get("incident_id", None)
    workflow_id = request.GET.get("workflow_id", None)
    if not workflow_id and not incident_id:
        messages.error(request, _("Missing data, incident report not created."))
        return redirect("incidents")

    incident = Incident.objects.filter(pk=incident_id).first()
    workflow = Workflow.objects.filter(id=workflow_id).first()

    if not workflow:
        messages.error(request, _("Workflow not found"))
        return redirect("incidents")

    if not incident:
        messages.error(request, _("Incident not found"))
        return redirect("incidents")

    if incident.incident_status == "CLOSE":
        messages.error(request, _("Incident is closed"))
        return redirect("incidents")

    if not incident.is_fillable(workflow):
        messages.error(request, _("Forbidden"))
        return redirect("incidents")

    user = request.user
    company_id = request.session.get("company_in_use")

    if not can_create_incident_report(user, incident, company_id):
        messages.error(request, _("Forbidden"))
        return redirect("incidents")
    else:
        form_list = get_forms_list(incident=incident)
        request.incident = incident_id
        request.workflow = workflow
        request.incident_workflow = None
        return WorkflowWizardView.as_view(
            form_list,
        )(request)


@login_required
@otp_required
@check_user_is_correct
def review_workflow(request):
    company_id = request.session.get("company_in_use")
    incident_workflow_id = request.GET.get("incident_workflow_id", None)
    if not incident_workflow_id:
        messages.error(request, _("No incident report could be found."))
        return redirect("incidents")
    user = request.user
    try:
        incident_workflow = IncidentWorkflow.objects.get(pk=incident_workflow_id)
    except IncidentWorkflow.DoesNotExist:
        messages.error(request, _("No incident report could be found."))
        return redirect("incidents")

    incident = incident_workflow.incident

    is_regulator_incidents = request.session.get("is_regulator_incidents", False)

    is_regulator_incident = (
        True
        if incident.regulator == user.regulators.first() and is_regulator_incidents
        else False
    )

    if incident_workflow:
        if can_access_incident(user, incident, company_id):
            form_list = get_forms_list(
                incident=incident_workflow.incident,
                workflow=incident_workflow.workflow,
                incident_workflow=incident_workflow,
                is_regulator=is_user_regulator(user),
                is_regulator_incident=is_regulator_incident,
                read_only=True,
            )
            request.incident_workflow = incident_workflow.id
            return WorkflowWizardView.as_view(
                form_list,
                read_only=True,
            )(request)
        else:
            messages.error(request, _("Forbidden"))
            return redirect("incidents")


@login_required
@otp_required
@check_user_is_correct
def edit_workflow(request):
    incident_id = request.GET.get("incident_id", None)
    workflow_id = request.GET.get("workflow_id", None)
    incident_workflow_id = request.GET.get("incident_workflow_id", None)
    user = request.user
    company_id = request.session.get("company_in_use")
    incident_workflow = None
    if not workflow_id and not incident_id and not incident_workflow_id:
        messages.error(request, _("No incident report could be found."))
        return redirect("incidents")
    elif workflow_id and incident_id:
        incident = Incident.objects.filter(pk=incident_id).first()
        workflow = Workflow.objects.filter(id=workflow_id).first()
        if not workflow:
            messages.error(request, _("Workflow not found"))
            return redirect("incidents")
        if not incident:
            messages.error(request, _("Incident not found"))
            return redirect("incidents")
        if incident.incident_status == "CLOSE":
            messages.error(request, _("Incident is closed"))
            return redirect("incidents")
        if not is_user_regulator(user):
            if not incident.is_fillable(workflow):
                messages.error(request, _("Forbidden"))
                return redirect("incidents")
    # for the moment we only pass the incident workflow for regulator
    elif incident_workflow_id and is_user_regulator(user):
        try:
            incident_workflow = IncidentWorkflow.objects.get(pk=incident_workflow_id)
        except IncidentWorkflow.DoesNotExist:
            messages.error(request, _("No incident report could be found."))
            return redirect("incidents")
    else:
        messages.error(request, _("Forbidden"))
        return redirect("incidents")

    is_regulator_incidents = request.session.get("is_regulator_incidents", False)

    if incident_id and can_edit_incident_report(user, incident, company_id):
        is_regulator_incident = (
            True
            if incident.regulator == user.regulators.first() and is_regulator_incidents
            else False
        )

        if incident_workflow is None:
            incident_workflow = IncidentWorkflow.objects.filter(
                incident=incident_id, workflow=workflow_id
            ).order_by("timestamp")
            incident_workflow = incident_workflow.last()

        if incident_workflow:
            request.incident = incident_workflow.incident.id
            form_list = get_forms_list(
                incident=incident_workflow.incident,
                workflow=incident_workflow.workflow,
                incident_workflow=incident_workflow,
                is_regulator=is_user_regulator(user),
                is_regulator_incident=is_regulator_incident,
            )
            request.incident_workflow = incident_workflow.id

            return WorkflowWizardView.as_view(
                form_list,
            )(request)
    elif incident_workflow and can_edit_incident_report(
        user, incident_workflow.incident, company_id
    ):
        is_regulator_incident = (
            True
            if incident_workflow.incident.regulator == user.regulators.first()
            and is_regulator_incidents
            else False
        )

        form_list = get_forms_list(
            incident=incident_workflow.incident,
            workflow=incident_workflow.workflow,
            incident_workflow=incident_workflow,
            is_regulator=is_user_regulator(user),
            is_regulator_incident=is_regulator_incident,
        )
        request.incident_workflow = incident_workflow.id

        return WorkflowWizardView.as_view(
            form_list,
        )(request)
    else:
        messages.error(request, _("Forbidden"))
        return redirect("incidents")
    messages.error(request, _("No incident report could be found."))
    return redirect("incidents")


@login_required
@otp_required
@regulator_role_required
@check_user_is_correct
@require_http_methods(["POST"])
def edit_incident(request, incident_id: int):
    """Returns the list of incident as regulator."""

    try:
        incident = Incident.objects.get(pk=incident_id)
    except Incident.DoesNotExist:
        messages.error(request, _("Incident not found"))
        return redirect("incidents")

    if not can_edit_incident_report(request.user, incident):
        return redirect("incidents")

    incident_form = IncidentStatusForm(request.POST, instance=incident)

    if incident_form.is_valid():
        incident = incident_form.save(commit=False)
        response = {"id": incident.pk}
        incident_status = incident_form.cleaned_data.get("incident_status")
        if incident_status == "CLOSE" and incident.sector_regulation.closing_email:
            send_email(incident.sector_regulation.closing_email, incident)

        for field_name in incident_form.cleaned_data:
            response[field_name] = incident_form.cleaned_data[field_name]

        old, new = incident_form.get_field_change("is_significative_impact")
        if old != new:
            if new is True:
                message = "IMP. True"
            else:
                message = "IMP. False"
            create_entry_log(request.user, incident, None, message, request)

        incident.save()

        return JsonResponse(response)

    return redirect("incidents")


@login_required
@otp_required
@check_user_is_correct
def access_log(request, incident_id: int):
    user = request.user
    company_id = request.session.get("company_in_use")
    try:
        incident = Incident.objects.get(pk=incident_id)
    except Incident.DoesNotExist:
        messages.error(request, _("Incident not found"))
        return redirect("incidents")

    if not can_access_incident(user, incident, company_id):
        messages.error(request, _("Forbidden"))
        return redirect("incidents")

    is_regulator_incidents = request.session.get("is_regulator_incidents", False)

    is_regulator_incident = (
        True
        if incident.regulator == user.regulators.first() and is_regulator_incidents
        else False
    )

    log = LogReportRead.objects.filter(incident=incident).order_by("-timestamp")
    if is_user_operator(user) or user_in_group(user, "IncidentUser"):
        log = log.exclude(user__regulatoruser__isnull=False)
    if is_regulator_incident:
        log = log.filter(user__regulatoruser__regulator=user.regulators.first())
    context = {
        "log": log,
        "incident": incident,
    }
    return render(request, "modals/access_log.html", context)


@login_required
@otp_required
@check_user_is_correct
def download_incident_pdf(request, incident_id: int):
    user = request.user
    company_id = request.session.get("company_in_use")

    try:
        incident = Incident.objects.get(pk=incident_id)
    except Incident.DoesNotExist:
        messages.error(request, _("Incident not found"))
        return redirect("incidents")

    if not can_access_incident(user, incident, company_id):
        messages.error(request, _("Forbidden"))
        return redirect("incidents")

    try:
        pdf_report = get_pdf_report(incident, None, request)
        create_entry_log(user, incident, None, "DOWNLOAD", request)
    except Exception:
        messages.error(request, _("An error occurred while generating the report."))
        return HttpResponseRedirect("/incidents")

    response = HttpResponse(pdf_report, content_type="application/pdf")

    latest_workflow = incident.get_latest_incident_workflow()
    timestamp = (
        latest_workflow.timestamp
        if latest_workflow
        else incident.incident_notification_date
    )
    filename = f"Incident_{incident.incident_id}_{timestamp:%Y-%m-%d}.pdf"
    response["Content-Disposition"] = f"attachment;filename={filename}"

    return response


@login_required
@otp_required
@check_user_is_correct
def download_incident_report_pdf(request, incident_workflow_id: int):
    user = request.user
    company_id = request.session.get("company_in_use")

    try:
        incident_workflow = IncidentWorkflow.objects.get(pk=incident_workflow_id)
        incident = incident_workflow.incident
    except IncidentWorkflow.DoesNotExist:
        messages.error(request, _("No incident report could be found."))
        return redirect("incidents")

    if not can_access_incident(user, incident, company_id):
        messages.error(request, _("Forbidden"))
        return redirect("incidents")
    try:
        pdf_report = get_pdf_report(incident, incident_workflow, request)
        create_entry_log(user, incident, incident_workflow, "DOWNLOAD", request)
    except Exception:
        messages.error(request, _("An error occurred while generating the report."))
        return HttpResponseRedirect("/incidents")

    response = HttpResponse(pdf_report, content_type="application/pdf")

    timestamp = incident_workflow.timestamp
    report_name = incident_workflow.workflow.name
    filename = f"{incident.incident_id}_{report_name}_{timestamp:%Y-%m-%d}.pdf"

    response["Content-Disposition"] = f"attachment;filename={filename}"

    return response


@login_required
@otp_required
@check_user_is_correct
def delete_incident(request, incident_id: int):
    user = request.user
    company_id = request.session.get("company_in_use")

    try:
        incident = Incident.objects.get(pk=incident_id)
    except Incident.DoesNotExist:
        messages.error(request, _("Incident not found"))
        return redirect("incidents")

    if not can_create_incident_report(user, incident, company_id):
        messages.error(request, _("Forbidden"))
        return redirect("incidents")

    try:
        incident = Incident.objects.get(pk=incident_id)
        if incident is not None:
            if incident.workflows.count() == 0:
                incident.delete()
                messages.success(request, _("The incident has been deleted."))
            else:
                messages.error(request, _("The incident could not be deleted."))
    except Exception:
        messages.error(request, _("An error occurred while deleting the incident."))
        return redirect("incidents")
    return redirect("incidents")


@login_required
@otp_required
@check_user_is_correct
def export_ciras(request):
    incidents = Incident.objects.all()
    data = []
    for incident in incidents:
        last_report = incident.get_latest_incident_workflow()
        incident_data = {
            "Name of operator": (
                incident.company.name if incident.company else incident.company_name
            ),
            "Reference": incident.incident_id,
            "Incident notification creation date": (
                incident.incident_notification_date.strftime("%d-%m-%Y %H:%M:%S")
                if incident.incident_notification_date
                else ""
            ),
            "Incident detection date": (
                last_report.report_timeline.incident_detection_date.strftime(
                    "%d-%m-%Y %H:%M:%S"
                )
                if last_report.report_timeline
                and last_report.report_timeline.incident_detection_date
                else ""
            ),
            "Incident start date": (
                last_report.report_timeline.incident_starting_date.strftime(
                    "%d-%m-%Y %H:%M:%S"
                )
                if last_report.report_timeline
                and last_report.report_timeline.incident_starting_date
                else ""
            ),
            "Incident resolution date": (
                last_report.report_timeline.incident_resolution_date.strftime(
                    "%d-%m-%Y %H:%M:%S"
                )
                if last_report.report_timeline
                and last_report.report_timeline.incident_resolution_date
                else ""
            ),
            "Legal basis": incident.sector_regulation,
            "Significative impact": (
                "yes" if incident.is_significative_impact else "no"
            ),
            "Incident Status": incident.get_incident_status_display(),
            "Incident notification manager": ", ".join(
                [
                    f"{incident.contact_firstname} {incident.contact_lastname}",
                    incident.contact_email,
                    incident.contact_telephone,
                ]
            ),
            "Incident technical contact": ", ".join(
                [
                    f"{incident.technical_firstname} {incident.technical_lastname}",
                    incident.technical_email,
                    incident.technical_telephone,
                ]
            ),
            "Report": (last_report.workflow if last_report.workflow else ""),
            "Report status": (
                last_report.get_review_status_display()
                if last_report.review_status
                else ""
            ),
            "Report creation date": (
                last_report.timestamp.strftime("%d-%m-%Y %H:%M:%S")
                if last_report.timestamp
                else ""
            ),
        }

        length_fixed_values = len(incident_data)

        for idx, sector in enumerate(incident.affected_sectors.all(), start=1):
            incident_data[f"Impacted sectors {idx}"] = str(sector).replace(
                " → ", " -> "
            )

        for answer in last_report.answer_set.all():
            question = answer.question_options.question
            str_answer = str(answer).replace(";", ",")
            if answer.predefined_answers.exists():
                for idx, pa in enumerate(answer.predefined_answers.all(), start=1):
                    pa_answer = str(pa).replace(";", ",")
                    if question.question_type == "SO":
                        incident_data[f"{question}"] = pa_answer
                    elif question.question_type == "ST":
                        if str_answer != "":
                            incident_data[f"{question}"] = (
                                f"{pa_answer} Details: {str_answer}"
                            )
                        else:
                            incident_data[f"{question}"] = pa_answer
                    else:
                        incident_data[f"{question} {idx}"] = pa_answer
            elif question.question_type == "CL" or question.question_type == "RL":
                for idx, item in enumerate(str_answer.split(","), start=1):
                    incident_data[f"{question} {idx}"] = item.strip()
            else:
                incident_data[f"{question}"] = str_answer

        data.append(incident_data)

    keys = []
    for entry in data:
        for k in entry.keys():
            if k not in keys:
                keys.append(k)

    def group_keys_by_index(keys):
        fixed_keys = keys[:length_fixed_values]
        dynamic_keys = keys[length_fixed_values:]
        groups = OrderedDict()
        for key in dynamic_keys:
            match = re.match(r"^(.*\D)\s*:?\s*(\d+)$", key)
            if match:
                prefix = match.group(1).strip()
                index = int(match.group(2))
                if prefix not in groups:
                    groups[prefix] = []
                groups[prefix].append((index, key))
            else:
                if key not in groups:
                    groups[key] = []
                groups[key].append((0, key))

        grouped_keys = []
        for _prefix, items in groups.items():
            items.sort(key=lambda x: x[0])
            grouped_keys.extend([key for _, key in items])
        return fixed_keys + grouped_keys

    keys = group_keys_by_index(keys)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="export_ciras.csv"'

    writer = csv.DictWriter(
        response, fieldnames=keys, extrasaction="ignore", quoting=csv.QUOTE_ALL
    )
    writer.writeheader()
    for entry in data:
        row = {key: entry.get(key, "") for key in keys}
        writer.writerow(row)

    return response


def is_incidents_report_limit_reached(request):
    if request.user.is_authenticated:
        # if a user make too many declaration we prevent to save
        number_preliminary_today = Incident.objects.filter(
            contact_user=request.user, incident_notification_date__date=date.today()
        ).count()
        if number_preliminary_today >= MAX_PRELIMINARY_NOTIFICATION_PER_DAY_PER_USER:
            messages.error(
                request,
                _(
                    "The daily limit of incident reports has been reached. Please try again tomorrow."
                ),
            )
            return True
    return False


# if there are no sectors or detection date needed don't show  condition dict for wizard
def show_form_condition(wizard):
    regulations_data = wizard.storage.get_step_data("1")
    regulators_data = wizard.storage.get_step_data("2")

    if not regulations_data or not regulators_data:
        return {"has_sector": False, "detection_date_needed": False}

    regulations_ids = regulations_data.getlist("1-regulations", [])
    regulator_ids = regulators_data.getlist("2-regulators", [])

    if not regulations_ids or not regulator_ids:
        return {"has_sector": False, "detection_date_needed": False}

    sector_regulation_qs = SectorRegulation.objects.filter(
        Q(regulation_id__in=regulations_ids) & Q(regulator_id__in=regulator_ids)
    )

    has_sector = sector_regulation_qs.filter(sectors__isnull=False).exists()
    detection_date_needed = sector_regulation_qs.filter(
        is_detection_date_needed=True
    ).exists()

    return {"has_sector": has_sector, "detection_date_needed": detection_date_needed}


class FormWizardView(SessionWizardView):
    """Wizard to manage the preliminary form."""

    template_name = "incidents/declaration.html"

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)

        context["steps"] = [
            _("Contact"),
            _("Legal bases"),
            _("Regulators"),
            _("Sectors"),
            _("Detection date"),
        ]
        context["action"] = "Create"
        context["is_regulator_incidents"] = self.request.session.get(
            "is_regulator_incidents", False
        )
        return context

    def render_goto_step(self, goto_step, **kwargs):
        form = self.get_form(self.steps.current, data=self.request.POST)

        if form.is_valid():
            current_data = form.cleaned_data
            storaged_data = self.get_cleaned_data_for_step(self.steps.current) or None

            if (
                storaged_data
                and self.steps.current in ["1", "2"]
                and current_data != storaged_data
            ):
                self.storage.set_step_data(goto_step, {})
                self.storage.set_step_data("3", {})

            self.storage.set_step_data(self.steps.current, self.process_step(form))

        elif int(self.steps.current) < int(goto_step):
            return self.render_revalidation_failure(self.steps.current, form)
        else:
            self.storage.set_step_data(self.steps.current, {})

        return super().render_goto_step(goto_step, **kwargs)

    def get_form_initial(self, step):
        def get_step_list(step_num, key):
            step_data = self.storage.get_step_data(step_num) or None
            if not step_data:
                return []

            return step_data.getlist(key, [])

        if step == "2":  # Regulators
            regulations = get_step_list("1", "1-regulations")
            return self.initial_dict.get(step, {"regulations": regulations})

        if step == "3":  # Sectors
            regulations = get_step_list("1", "1-regulations")
            regulators = get_step_list("2", "2-regulators")
            sectors = get_step_list("3", "3-sectors")

            return self.initial_dict.get(
                step,
                {
                    "regulations": regulations,
                    "regulators": regulators,
                    "sectors": sectors,
                },
            )

        return self.initial_dict.get(step, {})

    def done(self, form_list, **kwargs):
        if is_incidents_report_limit_reached(self.request):
            return HttpResponseRedirect("/incidents")

        user = self.request.user
        data = self.get_all_cleaned_data()
        company = (
            get_active_company_from_session(self.request)
            if not is_user_regulator(user)
            else None
        )
        regulator = user.regulators.first() if is_user_regulator(user) else None
        sectors_id = extract_ids(data.get("sectors", []))
        regulators_id = extract_ids(data.get("regulators", []))
        regulations_id = extract_ids(data.get("regulations", []))
        company_name = f"{data.get('company_name')} ({_('Not verified')})"
        if company or regulator:
            company_name = company.name if company else str(regulator)

        sector_regulations = (
            SectorRegulation.objects.filter(
                Q(sectors__in=sectors_id) | Q(sectors__isnull=True),
                regulator__in=regulators_id,
                regulation__in=regulations_id,
            )
            .order_by()
            .distinct()
        )

        incident_timezone = data.get("incident_timezone", TIME_ZONE)
        incident_detection_date = data.get("detection_date", None)

        if incident_detection_date:
            local_tz = pytz.timezone(incident_timezone)
            local_dt = local_tz.localize(incident_detection_date.replace(tzinfo=None))
            incident_detection_date = local_dt.astimezone(pytz.utc)

        for sector_regulation in sector_regulations:
            incident = Incident.objects.create(
                contact_lastname=data.get("contact_lastname"),
                contact_firstname=data.get("contact_firstname"),
                contact_title=data.get("contact_title"),
                contact_email=data.get("contact_email"),
                contact_telephone=data.get("contact_telephone"),
                # technical contact
                technical_lastname=data.get("technical_lastname"),
                technical_firstname=data.get("technical_firstname"),
                technical_title=data.get("technical_title"),
                technical_email=data.get("technical_email"),
                technical_telephone=data.get("technical_telephone"),
                incident_reference=data.get("incident_reference"),
                complaint_reference=data.get("complaint_reference"),
                contact_user=user,
                company=company,
                regulator=regulator,
                company_name=company_name,
                sector_regulation=sector_regulation,
                incident_timezone=data.get("incident_timezone", TIME_ZONE),
                incident_detection_date=incident_detection_date,
            )
            if incident:
                # Detect if a regulator is submitting the incident
                is_regulator_incidents = self.request.session.get(
                    "is_regulator_incidents", False
                )

                self.is_regulator_incident = (
                    True if regulator and is_regulator_incidents else False
                )
                # check if the detection date is over
                if sector_regulation.is_detection_date_needed:
                    sr_workflow = (
                        SectorRegulationWorkflow.objects.all()
                        .filter(
                            sector_regulation=sector_regulation,
                        )
                        .order_by("position")
                        .first()
                    )
                    # TO DO get the correct detection date
                    if sr_workflow.trigger_event_before_deadline == "DETECT_DATE":
                        dt = timezone.now() - incident.incident_detection_date
                        if (
                            round(dt.total_seconds() / 60 / 60, 0)
                            > sr_workflow.delay_in_hours_before_deadline
                        ):
                            sr_workflow.review_status = "OUT"
                            sr_workflow.save()

                sec = sector_regulation.sectors.values_list("id", flat=True)
                selected_sectors = Sector.objects.filter(id__in=sectors_id).values_list(
                    "id", flat=True
                )
                affected_sectors = selected_sectors & sec
                incident.affected_sectors.set(affected_sectors)
                # incident reference

                company_for_ref = (
                    company.identifier if company else data.get("company_name", "")[:4]
                )
                sector_for_ref = ""
                subsector_for_ref = ""

                for sector in sector_regulation.sectors.all():
                    if sector.id in sectors_id:
                        if subsector_for_ref == "":
                            subsector_for_ref = sector.acronym[:3]
                            if sector.parent:
                                sector_for_ref = sector.parent.acronym[:3]

                incidents_per_company = (
                    company.incident_set.filter(
                        incident_notification_date__year=date.today().year
                    ).count()
                    if company
                    else 0
                )
                if self.is_regulator_incident:
                    incidents_per_company = (
                        regulator.incident_set.filter(
                            incident_notification_date__year=date.today().year
                        ).count()
                        if regulator
                        else 0
                    )

                number_of_incident = f"{incidents_per_company:04}"
                incident.incident_id = (
                    f"{company_for_ref}_{sector_for_ref}_{subsector_for_ref}_"
                    f"{number_of_incident}_{date.today().year}"
                )

                incident.save()

                create_entry_log(user, incident, None, "CREATE", self.request)

                # send The email notification opening
                if sector_regulation.opening_email is not None:
                    send_email(
                        sector_regulation.opening_email,
                        incident,
                        send_to_observers=True,
                    )

        if sector_regulations.count() > 1:
            return (
                redirect("regulator_incidents")
                if self.is_regulator_incident
                else redirect("incidents")
            )

        sr_workflow = (
            SectorRegulationWorkflow.objects.filter(sector_regulation=sector_regulation)
            .order_by("position")
            .first()
        )

        if not sr_workflow or not sr_workflow.workflow:
            return redirect("incidents")

        query_params = urlencode(
            {
                "incident_id": incident.id,
                "workflow_id": sr_workflow.workflow.id,
            }
        )

        url = f"{reverse('create_workflow')}?{query_params}"
        return redirect(url)


class WorkflowWizardView(SessionWizardView):
    """Wizard to manage the different workflows."""

    template_name = "incidents/declaration.html"
    incident = None
    workflow = None
    incident_workflow = None
    read_only = False

    def __init__(self, read_only=False, **kwargs):
        self.form_list = kwargs.pop("form_list")
        self.read_only = read_only
        super().__init__(**kwargs)

    def get_form_kwargs(self, step=None):
        user = self.request.user
        if step is None:
            step = self.steps.current
        kwargs = super().get_form_kwargs(step)

        position = int(step)
        is_regulator_incidents = self.request.session.get(
            "is_regulator_incidents", False
        )

        if self.request.incident_workflow:
            self.incident_workflow = IncidentWorkflow.objects.get(
                pk=self.request.incident_workflow
            )
            self.incident = self.incident_workflow.incident
            self.workflow = self.incident_workflow.workflow
            self.is_regulator_incident = (
                True
                if self.incident.regulator == user.regulators.first()
                and is_regulator_incidents
                else False
            )
            regulation_sector_has_impacts = Impact.objects.filter(
                regulations=self.incident.sector_regulation.regulation,
                sectors__in=self.incident.affected_sectors.all(),
            ).exists()

            self.workflow.is_impact_needed = bool(
                self.workflow.is_impact_needed and regulation_sector_has_impacts
            )

            is_new_incident_workflow = not self.read_only and (
                is_user_regulator(user) == self.is_regulator_incident
            )

            self.categories_workflow = get_workflow_categories(
                self.workflow,
                self.incident_workflow,
                is_new_incident_workflow,
            )

            if position == 0:
                kwargs.update(
                    {
                        "instance": self.incident_workflow.report_timeline,
                        "incident": self.incident,
                    }
                )
            # Regulator case
            elif (
                position == len(self.form_list) - 2
                and self.workflow.is_impact_needed
                and is_user_regulator(user)
                and not self.is_regulator_incident
            ):
                kwargs.update({"incident": self.incident})
            elif (
                position == len(self.form_list) - 1
                and is_user_regulator(user)
                and not self.is_regulator_incident
            ):
                kwargs.update({"instance": self.incident_workflow})
            # Operator case
            elif (
                position == len(self.form_list) - 1
                and self.workflow.is_impact_needed
                and (not is_user_regulator(user) or self.is_regulator_incident)
            ):
                kwargs.update({"incident": self.incident})
            else:
                # regulator pass directly the incident_workflow
                kwargs.update(
                    {
                        "position": position - 1,
                        "incident_workflow": self.incident_workflow,
                        "categories_workflow": self.categories_workflow,
                        "is_new_incident_workflow": not self.read_only
                        and (is_user_regulator(user) == self.is_regulator_incident),
                    }
                )
        elif self.request.incident:
            self.incident = Incident.objects.get(pk=self.request.incident)
            self.is_regulator_incident = (
                True
                if self.incident.regulator == user.regulators.first()
                and is_regulator_incidents
                else False
            )

            if not self.request.workflow:
                self.workflow = self.incident.get_next_step()
            else:
                self.workflow = self.request.workflow

            regulation_sector_has_impacts = Impact.objects.filter(
                regulations=self.incident.sector_regulation.regulation,
                sectors__in=self.incident.affected_sectors.all(),
            ).exists()

            self.workflow.is_impact_needed = bool(
                self.workflow.is_impact_needed and regulation_sector_has_impacts
            )

            is_new_incident_workflow = not self.read_only and (
                is_user_regulator(user) == self.is_regulator_incident
            )

            self.categories_workflow = get_workflow_categories(
                self.workflow,
                self.incident_workflow,
                is_new_incident_workflow,
            )
            if position == 0:
                kwargs.update({"incident": self.incident})
            elif position == len(self.form_list) - 1 and self.workflow.is_impact_needed:
                kwargs.update({"incident": self.incident})
            else:
                kwargs.update(
                    {
                        "position": position - 1,
                        "workflow": self.workflow,
                        "incident": self.incident,
                        "categories_workflow": self.categories_workflow,
                        "is_new_incident_workflow": not self.read_only
                        and (is_user_regulator(user) == self.is_regulator_incident),
                    }
                )

        return kwargs

    def get(self, request, *args, **kwargs):
        incident_workflow_id = request.GET.get("incident_workflow_id", None)
        if incident_workflow_id:
            company_id = request.session.get("company_in_use")
            user = request.user
            incident_workflow = IncidentWorkflow.objects.get(pk=incident_workflow_id)
            incident = incident_workflow.incident

            if incident_workflow and can_access_incident(user, incident, company_id):
                create_entry_log(
                    user, incident_workflow.incident, incident_workflow, "READ", request
                )

        return super().get(self, request, *args, **kwargs)

    def get_form(self, step=None, data=None, files=None):
        if step is None:
            step = self.steps.current
        position = int(step)
        user = self.request.user
        self.is_review = False

        # Operator : Complete an existing workflow or see historic
        # Regulator : See the report
        form = super().get_form(step=step, data=data, files=files)

        # Read only for regulator except for last form (save comment)
        # Read only for operator review (read_only = True)
        if self.read_only:
            last_form_index = -1
        else:
            last_form_index = len(self.form_list) - 1
        if (
            (is_user_regulator(user) and position != last_form_index)
            and not self.is_regulator_incident
            or self.read_only
        ):
            self.is_review = True
            for field in form.fields:
                form.fields[field].disabled = True
                form.fields[field].required = False

                # replace following widget by more readable in read only
                if (
                    form.fields[field].widget.__class__.__name__
                    == "DropdownCheckboxSelectMultiple"
                ):
                    COUNTRY_DICT = dict(countries)
                    REGIONAL_DICT = dict(REGIONAL_AREA)
                    initial = " - ".join(
                        map(
                            lambda val: str(
                                COUNTRY_DICT.get(val, REGIONAL_DICT.get(val, val))
                            ),
                            form.fields[field].initial,
                        )
                    )

                    new_field = forms.CharField(
                        required=False,
                        disabled=True,
                        label=form.fields[field].label,
                        initial=initial,
                    )
                    form.fields[field] = new_field

        return form

    def get_context_data(self, form, **kwargs):
        user = self.request.user
        context = super().get_context_data(form=form, **kwargs)

        if self.workflow is not None:
            context["action"] = (
                "Edit"
                if self.read_only
                or (is_user_regulator(user) and not self.is_regulator_incident)
                else "Create"
            )
            context["is_regulator_incident"] = self.is_regulator_incident
            context["steps"] = []
            context["steps"].append(_("Incident Timeline"))
            context["steps"].extend(self.categories_workflow)
            if self.workflow.is_impact_needed:
                regulation_sector_has_impacts = Impact.objects.filter(
                    regulations=self.incident.sector_regulation.regulation,
                    sectors__in=self.incident.affected_sectors.all(),
                ).exists()
                if regulation_sector_has_impacts:
                    context["steps"].append(_("Impacts"))

            user = self.request.user
            if is_user_regulator(user) and not self.is_regulator_incident:
                context["steps"].append(_("Comment/Explanation"))
        return context

    def render_goto_step(self, goto_step, **kwargs):
        current_step = self.steps.current
        form = self.get_form(
            current_step, data=self.request.POST, files=self.request.FILES
        )

        if form.is_valid():
            self.storage.set_step_data(current_step, self.process_step(form))
            self.storage.set_step_files(current_step, self.process_step_files(form))
        elif int(current_step) < int(goto_step):
            # If the form is not valid, we don't allow to go to the next step
            return self.render_revalidation_failure(current_step, form)

        # If the user is in review mode and is going to the last step,
        # we ensure that all previous steps are stored, this avoid render validation.
        if self.is_review and not self.read_only and goto_step == self.steps.last:
            for step in self.steps.all:
                if step == goto_step or self.storage.get_step_data(step):
                    continue
                form = self.get_form(step)
                self.storage.set_step_data(step, self.process_step(form))

        return super().render_goto_step(goto_step, **kwargs)

    def done(self, form_list, **kwargs):
        user = self.request.user
        data = self.get_all_cleaned_data()
        if (
            not is_user_regulator(user) or self.is_regulator_incident
        ) and not self.read_only:
            incident_timezone = data.get("incident_timezone", TIME_ZONE)
            incident_starting_date = data.get("incident_starting_date", None)
            incident_detection_date = data.get("incident_detection_date", None)
            incident_resolution_date = data.get("incident_resolution_date", None)
            local_tz = pytz.timezone(incident_timezone)
            email = self.workflow.submission_email or None
            self.incident = self.incident or get_object_or_404(
                Incident, pk=self.request.incident
            )
            self.incident.review_status = "DELIV"
            self.incident.incident_timezone = incident_timezone

            if incident_starting_date:
                incident_starting_date = convert_to_utc(
                    incident_starting_date, local_tz
                )

            if (
                incident_detection_date
                and not self.incident.sector_regulation.is_detection_date_needed
            ):
                self.incident.incident_detection_date = convert_to_utc(
                    incident_detection_date, local_tz
                )

            if incident_resolution_date:
                incident_resolution_date = convert_to_utc(
                    incident_resolution_date, local_tz
                )

            self.incident.save()
            # create the report timeline
            report_timeline = ReportTimeline.objects.create(
                report_timeline_timezone=incident_timezone,
                incident_starting_date=incident_starting_date,
                incident_detection_date=self.incident.incident_detection_date,
                incident_resolution_date=incident_resolution_date,
            )
            # manage question
            incident_workflow = save_answers(
                data, self.incident, self.workflow, report_timeline
            )
            create_entry_log(
                user, self.incident, incident_workflow, "CREATE", self.request
            )

            if email and not self.incident.incident_status == "CLOSE":
                send_email(email, self.incident, send_to_observers=True)
        # save the comment if the user is regulator
        elif is_user_regulator(user) and not self.read_only:
            incident_workflow = (
                IncidentWorkflow.objects.all()
                .filter(incident=self.incident, workflow=self.workflow)
                .order_by("-timestamp")
                .first()
            )
            incident_workflow.comment = data.get("comment", None)
            review_status = data.get("review_status", None)
            if incident_workflow.review_status != review_status:
                if (
                    incident_workflow.incident.sector_regulation.report_status_changed_email
                    and not incident_workflow.incident.incident_status == "CLOSE"
                ):
                    send_email(
                        incident_workflow.incident.sector_regulation.report_status_changed_email,
                        incident_workflow.incident,
                    )
            if review_status is not None:
                incident_workflow.review_status = review_status
                review_status_txt = next(
                    (
                        label
                        for code, label in WORKFLOW_REVIEW_STATUS
                        if code == review_status
                    ),
                    None,
                )
                create_entry_log(
                    user,
                    self.incident,
                    incident_workflow,
                    "REVIEW STATUS: " + review_status_txt,
                    self.request,
                )
            incident_workflow.save()
            create_entry_log(
                user,
                incident_workflow.incident,
                incident_workflow,
                "COMMENT",
                self.request,
            )

        return (
            redirect("regulator_incidents")
            if self.is_regulator_incident
            else redirect("incidents")
        )


def save_answers(data=None, incident=None, workflow=None, report_timeline=None):
    """Save the answers."""
    prefix = "__question__"
    questions_data = {
        key[slice(len(prefix), None)]: value
        for key, value in data.items()
        if key.startswith(prefix)
    }

    # We create a new incident workflow in all the case (history)
    incident_workflow = IncidentWorkflow.objects.create(
        incident=incident, workflow=workflow, report_timeline=report_timeline
    )
    incident_workflow.save()
    # TO DO manage impact
    if workflow.is_impact_needed:
        impacts = data.get("impacts", [])
        incident_workflow.impacts.set(impacts)
        incident = incident_workflow.incident
        incident.is_significative_impact = False

        if len(impacts) > 0:
            incident.is_significative_impact = True

        incident.save()

    for key, value in questions_data.items():
        question_id = None
        try:
            question_id = int(key)
        except Exception:
            pass
        if question_id:
            predefined_answers = []
            question_option = QuestionOptions.objects.get(pk=key)
            question = question_option.question
            question_type = question.question_type

            if question_type == "FREETEXT":
                answer = value
            elif question_type == "DATE":
                if value:
                    answer = value.strftime("%Y-%m-%d %H:%M")
                else:
                    answer = None
            elif question_type == "CL" or question_type == "RL":
                answer = ",".join(map(str, value))
            else:  # MULTI
                for val in value:
                    predefined_answers.append(PredefinedAnswer.objects.get(pk=val))
                answer = questions_data.get(key + "_freetext_answer", None)
            answer_object = Answer.objects.create(
                incident_workflow=incident_workflow,
                question_options=question_option,
                answer=answer,
            )
            answer_object.predefined_answers.set(predefined_answers)

    return incident_workflow


def can_redirect(url: str) -> bool:
    """
    Check if a redirect is authorised.
    """
    o = urlparse(url)
    return o.netloc in PUBLIC_URL


def extract_ids(data: list) -> list:
    return [int(item) for item in data if item.isdigit()]


def convert_to_utc(date, local_tz):
    if date:
        local_dt = local_tz.localize(date.replace(tzinfo=None))
        return local_dt.astimezone(pytz.utc)
    return None


def create_entry_log(user, incident, incident_report, action, request=None):
    role = _("User")
    entity_name = ""

    if is_user_operator(user) and request:
        active_company = get_active_company_from_session(request)
        cu = CompanyUser.objects.filter(user=user, company=active_company).first()
        if cu and cu.is_company_administrator:
            role = _("Administrator")
        entity_name = active_company.name

    elif is_user_regulator(user):
        regulator = user.regulators.first()
        ru = RegulatorUser.objects.filter(user=user, regulator=regulator).first()
        if ru and ru.is_regulator_administrator:
            role = _("Administrator")
        entity_name = regulator.name

    log = LogReportRead.objects.create(
        user=user,
        incident=incident,
        incident_report=incident_report,
        action=action,
        role=role,
        entity_name=entity_name,
    )
    log.save()

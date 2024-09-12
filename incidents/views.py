# import hashlib
# import json

from datetime import date
from urllib.parse import urlparse

import pytz
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django_countries import countries
from django_otp.decorators import otp_required
from formtools.wizard.views import SessionWizardView

from governanceplatform.helpers import (
    can_access_incident,
    can_create_incident_report,
    can_edit_incident_report,
    get_active_company_from_session,
    is_observer_user,
    is_observer_user_viewving_all_incident,
    is_user_operator,
    is_user_regulator,
    user_in_group,
)
from governanceplatform.models import Regulation, Regulator, Sector
from governanceplatform.settings import (
    MAX_PRELIMINARY_NOTIFICATION_PER_DAY_PER_USER,
    PUBLIC_URL,
    SITE_NAME,
    TIME_ZONE,
)
from theme.globals import REGIONAL_AREA

from .decorators import regulator_role_required
from .email import send_email
from .filters import IncidentFilter
from .forms import (
    ContactForm,
    ImpactForm,
    IncidenteDateForm,
    IncidentStatusForm,
    IncidentWorkflowForm,
    RegulationForm,
    RegulatorForm,
    get_forms_list,
)
from .models import (
    Answer,
    Incident,
    IncidentWorkflow,
    LogReportRead,
    PredefinedAnswer,
    Question,
    SectorRegulation,
    SectorRegulationWorkflow,
    Workflow,
)
from .pdf_generation import get_pdf_report


@login_required
@otp_required
def get_incidents(request):
    """Returns the list of incidents depending on the account type."""
    user = request.user
    incidents = Incident.objects.order_by("-incident_notification_date")

    # Save filter params in user's session

    if "reset" in request.GET:
        if "filter_params" in request.session:
            del request.session["filter_params"]
        return redirect("incidents")

    if request.GET:
        request.session["filter_params"] = request.GET

    filter_params = request.session.get("filter_params", request.GET)

    if is_user_regulator(user):
        # Filter incidents by regulator

        incidents = incidents.filter(
            sector_regulation__regulator__in=user.regulators.all()
        )
        if user_in_group(user, "RegulatorUser"):
            # RegulatorUser has access to all incidents linked by sectors.
            incidents = incidents.filter(
                affected_sectors__in=request.user.get_sectors().all()
            ).distinct()
        for incident in incidents:
            incident.formsWorkflow = []
            for workflow_completed in incident.get_workflows_completed():
                incident.formsWorkflow.append(
                    IncidentWorkflowForm(instance=workflow_completed)
                )
            incident.formsStatus = IncidentStatusForm(
                instance=incident,
            )

        f = IncidentFilter(filter_params, queryset=incidents)
    elif user_in_group(user, "OperatorAdmin"):
        # OperatorAdmin can see all the reports of the selected company.
        incidents = incidents.filter(company__id=request.session.get("company_in_use"))
        f = IncidentFilter(filter_params, queryset=incidents)
    elif is_observer_user_viewving_all_incident(user):
        incidents = Incident.objects.all().order_by("-incident_notification_date")
        f = IncidentFilter(filter_params, queryset=incidents)
    elif user_in_group(user, "OperatorUser"):
        # OperatorUser see his incident and the one oh his sectors for the company
        query1 = incidents.filter(
            company__id=request.session.get("company_in_use"),
            affected_sectors__in=user.sectors.all(),
        )
        query2 = incidents.filter(contact_user=user)
        incidents = (query1 | query2).distinct()
        f = IncidentFilter(filter_params, queryset=incidents)
    else:
        # OperatorUser and IncidentUser can see only their reports.
        incidents = incidents.filter(contact_user=user)
        f = IncidentFilter(filter_params, queryset=incidents)

    if request.GET.get("incidentId"):
        # Search by incident id
        incidents = incidents.filter(
            incident_id__icontains=request.GET.get("incidentId")
        ).distinct()

    # Show 10 incidents per page.
    incident_list = f.qs
    paginator = Paginator(incident_list, 10)
    page_number = request.GET.get("page", 1)
    try:
        response = paginator.page(page_number)
    except PageNotAnInteger:
        response = paginator.page(1)
    except EmptyPage:
        response = paginator.page(paginator.num_pages)

    # add paggination to the regular incidents view.
    html_view = "operator/incidents.html"
    if is_user_regulator(request.user):
        html_view = "regulator/incidents.html"
    elif is_observer_user(request.user):
        html_view = "observer/incidents.html"

    is_filtered = {k: v for k, v in filter_params.items() if k != "page"}

    return render(
        request,
        html_view,
        context={
            "site_name": SITE_NAME,
            "paginator": paginator,
            "filter": f,
            "incidents": response,
            "is_filtered": bool(is_filtered),
        },
    )


@login_required
@otp_required
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
            "3": show_sector_form_condition,
            "4": show_dection_date_form_condition,
        },
    )(request)


@login_required
@otp_required
def get_next_workflow(request, form_list=None, incident_id=None):
    if form_list is None and incident_id is not None:
        incident = Incident.objects.get(id=incident_id)
        form_list = get_forms_list(incident=incident)
    if incident_id is not None:
        request.incident = incident_id
        request.incident_workflow = None
    return WorkflowWizardView.as_view(
        form_list,
    )(request)


@login_required
@otp_required
def create_workflow(request):
    incident_id = request.GET.get("incident_id", None)
    workflow_id = request.GET.get("workflow_id", None)
    if not workflow_id and not incident_id:
        messages.error(request, _("Missing data to create the incident report"))
        return redirect("incidents")

    incident = Incident.objects.filter(pk=incident_id).first()
    workflow = Workflow.objects.filter(id=workflow_id).first()

    if not workflow:
        messages.error(request, _("Workflow not found"))
        return redirect("incidents")

    if not incident:
        messages.error(request, _("Incident not found"))
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
def review_workflow(request):
    company_id = request.session.get("company_in_use")
    incident_workflow_id = request.GET.get("incident_workflow_id", None)
    if not incident_workflow_id:
        messages.warning(request, _("No incident report could be found."))
        return redirect("incidents")
    user = request.user
    incident_workflow = IncidentWorkflow.objects.get(pk=incident_workflow_id)
    incident = incident_workflow.incident

    if incident_workflow:
        if can_access_incident(user, incident, company_id):
            form_list = get_forms_list(
                incident=incident_workflow.incident,
                workflow=incident_workflow.workflow,
                is_regulator=is_user_regulator(user),
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
def edit_workflow(request):
    incident_id = request.GET.get("incident_id", None)
    workflow_id = request.GET.get("workflow_id", None)
    incident_workflow_id = request.GET.get("incident_workflow_id", None)
    user = request.user
    company_id = request.session.get("company_in_use")
    incident_workflow = None
    if not workflow_id and not incident_id and not incident_workflow_id:
        messages.warning(request, _("No incident report could be found."))
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
        if not is_user_regulator(user):
            if not incident.is_fillable(workflow):
                messages.error(request, _("Forbidden"))
                return redirect("incidents")
    # for the moment we only pass the incident workflow for regulator
    elif incident_workflow_id and is_user_regulator(user):
        incident_workflow = IncidentWorkflow.objects.get(pk=incident_workflow_id)
    else:
        messages.error(request, _("Forbidden"))
        return redirect("incidents")
    if incident_id and can_edit_incident_report(user, incident, company_id):
        if incident_workflow is None:
            incident_workflow = IncidentWorkflow.objects.filter(
                incident=incident_id, workflow=workflow_id
            ).order_by("timestamp")
            incident_workflow = incident_workflow.last()
            request.incident = incident_workflow.incident.id

        if incident_workflow:
            form_list = get_forms_list(
                incident=incident_workflow.incident,
                workflow=incident_workflow.workflow,
                is_regulator=is_user_regulator(user),
            )
            request.incident_workflow = incident_workflow.id

            return WorkflowWizardView.as_view(
                form_list,
            )(request)
    elif incident_workflow and can_edit_incident_report(
        user, incident_workflow.incident, company_id
    ):
        form_list = get_forms_list(
            incident=incident_workflow.incident,
            workflow=incident_workflow.workflow,
            is_regulator=is_user_regulator(user),
        )
        request.incident_workflow = incident_workflow.id

        return WorkflowWizardView.as_view(
            form_list,
        )(request)
    else:
        messages.error(request, _("Forbidden"))
        return redirect("incidents")
    messages.warning(request, _("No incident report could be found."))
    return redirect("incidents")


@login_required
@otp_required
def edit_impacts(request, incident_id=None):
    # OperatorAdmin can access only incidents related to selected company.
    if (
        user_in_group(request.user, "OperatorAdmin")
        and not Incident.objects.filter(
            pk=incident_id, company__id=request.session.get("company_in_use")
        ).exists()
    ):
        return HttpResponseRedirect("/incidents")
    # OperatorStaff and IncidentUser can access only their incidents.
    if (
        not is_user_regulator(request.user)
        and not user_in_group(request.user, "OperatorAdmin")
        and not Incident.objects.filter(
            pk=incident_id, contact_user=request.user
        ).exists()
    ):
        return HttpResponseRedirect("/incidents")

    if incident_id is not None:
        incident = Incident.objects.get(id=incident_id)

    form = ImpactForm(
        incident=incident, data=request.POST if request.method == "POST" else None
    )

    if request.method == "POST":
        if form.is_valid():
            incident.impacts.set(form.cleaned_data["impacts"])
            if len(form.cleaned_data["impacts"]) > 0:
                incident.is_significative_impact = True
            else:
                incident.is_significative_impact = False
            incident.save()
            return HttpResponseRedirect("/incidents")

    return render(request, "edit_impacts.html", {"form": form, "incident": incident})


@login_required
@otp_required
@regulator_role_required
def get_regulator_incident_edit_form(request, incident_id: int):
    """Returns the list of incident as regulator."""
    # RegulatorUser can access only incidents from accessible sectors.
    if not can_edit_incident_report(request.user, Incident.objects.get(pk=incident_id)):
        return HttpResponseRedirect("/incidents")

    workflow_id = request.GET.get("workflow_id", None)
    incident = Incident.objects.get(pk=incident_id)
    if workflow_id and IncidentWorkflow.objects.filter(pk=workflow_id).exists():
        workflow = IncidentWorkflow.objects.get(pk=workflow_id)
        workflow_form = IncidentWorkflowForm(
            instance=workflow,
            data=request.POST if request.method == "POST" else None,
        )
        if request.method == "POST":
            if workflow_form.is_valid():
                response = {"id": workflow.pk}
                for field_name, field_value in workflow_form.cleaned_data.items():
                    if field_value:
                        response[field_name] = field_value
                        setattr(workflow, field_name, field_value)
                    else:
                        response[field_name] = workflow_form.initial[field_name]
                        setattr(
                            workflow,
                            field_name,
                            workflow_form.initial[field_name],
                        )
                    if field_name == "review_status":
                        if incident.sector_regulation.report_status_changed_email:
                            send_email(
                                incident.sector_regulation.report_status_changed_email,
                                incident,
                            )
                workflow.save()

            return JsonResponse(response)

    incident_form = IncidentStatusForm(
        instance=incident, data=request.POST if request.method == "POST" else None
    )
    if request.method == "POST":
        # TO DO : improve, but we can't check if the form is valid because we send only one value
        if incident_form is not None:
            # need to validate to get the cleaned data
            incident_form.is_valid()
            response = {"id": incident.pk}
            for field_name, field_value in incident_form.cleaned_data.items():
                if field_name and field_value is not None:
                    response[field_name] = field_value
                    setattr(incident, field_name, field_value)
                    if field_name == "incident_status" and field_value == "CLOSE":
                        if incident.sector_regulation.closing_email:
                            send_email(
                                incident.sector_regulation.closing_email, incident
                            )

                else:
                    response[field_name] = incident_form.initial[field_name]
                    setattr(
                        incident,
                        field_name,
                        incident_form.initial[field_name],
                    )
            incident.save()

    return JsonResponse(response)


@login_required
@otp_required
def get_edit_incident_timeline_form(request, incident_id: int):
    # RegulatorUser can access only incidents from accessible sectors.
    if (
        user_in_group(request.user, "RegulatorUser")
        and not Incident.objects.filter(
            pk=incident_id, affected_sectors__in=request.user.sectors.all()
        ).exists()
    ):
        return HttpResponseRedirect("/incidents")
    # OperatorAdmin can access only incidents related to selected company.
    elif (
        user_in_group(request.user, "OperatorAdmin")
        and not Incident.objects.filter(
            pk=incident_id, company__id=request.session.get("company_in_use")
        ).exists()
    ):
        return HttpResponseRedirect("/incidents")
    # OperatorStaff and IncidentUser can access only their reports.
    elif (
        not is_user_regulator(request.user)
        and not user_in_group(request.user, "OperatorAdmin")
        and not Incident.objects.filter(
            pk=incident_id, contact_user=request.user
        ).exists()
    ):
        return HttpResponseRedirect("/incidents")

    incident = Incident.objects.get(pk=incident_id)

    incident_date_form = IncidenteDateForm(
        instance=incident, data=request.POST if request.method == "POST" else None
    )
    if request.method == "POST":
        if incident_date_form.is_valid():
            incident_date_form.save()
            messages.success(
                request,
                f"Incident {incident.incident_id} has been successfully saved.",
            )
            response = HttpResponseRedirect(
                request.session.get("return_page", "/incidents")
            )
            try:
                del request.session["return_page"]
            except KeyError:
                pass

            return response

    if not request.session.get("return_page"):
        request.session["return_page"] = request.headers.get("referer", "/incidents")

    return render(
        request,
        "edit_incident_timeline.html",
        context={
            "form": incident_date_form,
            "incident": incident,
        },
    )


@login_required
@otp_required
def access_log(request, incident_id: int):
    user = request.user
    incident = Incident.objects.get(pk=incident_id)
    company_id = request.session.get("company_in_use")

    if not can_access_incident(user, incident, company_id):
        messages.error(request, _("Forbidden"))
        return redirect("incidents")

    log = LogReportRead.objects.filter(incident=incident).order_by("-timestamp")
    if is_user_operator(user):
        log = log.exclude(user__regulatoruser__isnull=False)
    context = {
        "log": log,
        "incident": incident,
    }
    return render(request, "modals/access_log.html", context)


@login_required
@otp_required
def download_incident_pdf(request, incident_id: int):
    user = request.user
    incident = Incident.objects.get(pk=incident_id)
    company_id = request.session.get("company_in_use")

    if not can_access_incident(user, incident, company_id):
        messages.error(request, _("Forbidden"))
        return redirect("incidents")
    else:
        try:
            pdf_report = get_pdf_report(incident, None, request)
            create_entry_log(user, incident, None, "DOWNLOAD")
        except Exception:
            messages.warning(
                request, _("An error occurred while generating the report.")
            )
            return HttpResponseRedirect("/incidents")

        response = HttpResponse(pdf_report, content_type="application/pdf")
        response[
            "Content-Disposition"
        ] = f"attachment;filename=Incident_{incident_id}_{date.today()}.pdf"

        return response


@login_required
@otp_required
def download_incident_report_pdf(request, incident_workflow_id: int):
    user = request.user
    incident_workflow = IncidentWorkflow.objects.get(pk=incident_workflow_id)
    incident = incident_workflow.incident
    company_id = request.session.get("company_in_use")

    if not can_access_incident(user, incident, company_id):
        messages.error(request, _("Forbidden"))
        return redirect("incidents")
    else:
        try:
            pdf_report = get_pdf_report(incident, incident_workflow, request)
            create_entry_log(user, incident, incident_workflow, "DOWNLOAD")
        except Exception:
            messages.warning(
                request, _("An error occurred while generating the report.")
            )
            return HttpResponseRedirect("/incidents")

        response = HttpResponse(pdf_report, content_type="application/pdf")
        response[
            "Content-Disposition"
        ] = f"attachment;filename=Incident_{incident_workflow}_{date.today()}.pdf"

        return response


@login_required
@otp_required
def delete_incident(request, incident_id: int):
    user = request.user
    incident = Incident.objects.get(pk=incident_id)
    company_id = request.session.get("company_in_use")

    if not can_create_incident_report(user, incident, company_id):
        messages.error(request, _("Forbidden"))
        return redirect("incidents")
    else:
        try:
            incident = Incident.objects.get(pk=incident_id)
            if incident is not None:
                if incident.workflows.count() == 0:
                    incident.delete()
                    messages.info(request, _("The incident has been deleted."))
                else:
                    messages.warning(request, _("The incident could not be deleted."))
        except Exception:
            messages.warning(
                request, _("An error occurred while deleting the incident.")
            )
            return redirect("incidents")
        return redirect("incidents")


def is_incidents_report_limit_reached(request):
    if request.user.is_authenticated:
        # if a user make too many declaration we prevent to save
        number_preliminary_today = Incident.objects.filter(
            contact_user=request.user, incident_notification_date=date.today()
        ).count()
        if number_preliminary_today >= MAX_PRELIMINARY_NOTIFICATION_PER_DAY_PER_USER:
            messages.warning(
                request,
                _(
                    "The daily limit of incident reports has been reached. Please try again tomorrow."
                ),
            )
            return True
    return False


# remove a prefix on a multivaluedict object
def get_temporary_cleaned_data(MultivalueDict, prefix):
    for d in list(MultivalueDict):
        if d.startswith(prefix):
            MultivalueDict.setlist(d[2:], MultivalueDict.getlist(d))
            del MultivalueDict[d]
    return MultivalueDict


# if there are no sectors don't show sectors, condition dict for wizard
def show_sector_form_condition(wizard):
    data1 = wizard.storage.get_step_data("1")
    if data1 is not None:
        data1 = get_temporary_cleaned_data(data1, "1-")
    data2 = wizard.storage.get_step_data("2")
    if data2 is not None:
        data2 = get_temporary_cleaned_data(data2, "2-")
    temp_regulator_form = RegulatorForm(
        data=data1,
    )
    regulators = None
    if data1 is not None and data1.get("regulators") is not None:
        regulators = Regulator.objects.all().filter(pk__in=data1.getlist("regulators"))
    temp_regulation_form = RegulationForm(
        data=data2, initial={"regulators": regulators}
    )
    data_regulation = data_regulator = None

    if temp_regulation_form.is_valid() and temp_regulator_form.is_valid():
        data_regulation = temp_regulation_form.cleaned_data
        data_regulator = temp_regulator_form.cleaned_data

    has_sector = False
    if data_regulator is not None and data_regulation is not None:
        ids = data_regulation.get("regulations", "")
        regulations = Regulation.objects.filter(id__in=ids)
        ids = data_regulator.get("regulators", "")
        regulators = Regulator.objects.filter(id__in=ids)
        sector_regulations = SectorRegulation.objects.all().filter(
            regulation__in=regulations, regulator__in=regulators
        )

        for sector_regulation in sector_regulations:
            for __sector in sector_regulation.sectors.all():
                has_sector = True
    return has_sector


def show_dection_date_form_condition(wizard):
    data1 = wizard.storage.get_step_data("1")
    if data1 is not None:
        data1 = get_temporary_cleaned_data(data1, "1-")
    data2 = wizard.storage.get_step_data("2")
    if data2 is not None:
        data2 = get_temporary_cleaned_data(data2, "2-")
    temp_regulator_form = RegulatorForm(
        data=data1,
    )
    regulators = None
    if data1 is not None and data1.get("regulators") is not None:
        regulators = Regulator.objects.all().filter(pk__in=data1.getlist("regulators"))
    temp_regulation_form = RegulationForm(
        data=data2, initial={"regulators": regulators}
    )
    data_regulation = data_regulator = None

    if temp_regulation_form.is_valid() and temp_regulator_form.is_valid():
        data_regulation = temp_regulation_form.cleaned_data
        data_regulator = temp_regulator_form.cleaned_data

    detection_date_needed = False
    if data_regulator is not None and data_regulation is not None:
        ids = data_regulation.get("regulations", "")
        regulations = Regulation.objects.filter(id__in=ids)
        ids = data_regulator.get("regulators", "")
        regulators = Regulator.objects.filter(id__in=ids)
        sector_regulations = SectorRegulation.objects.all().filter(
            regulation__in=regulations, regulator__in=regulators
        )

        for sector_regulation in sector_regulations:
            if sector_regulation.is_detection_date_needed:
                detection_date_needed = True
    return detection_date_needed


class FormWizardView(SessionWizardView):
    """Wizard to manage the preliminary form."""

    template_name = "declaration.html"

    def __init__(self, **kwargs):
        self.form_list = kwargs.pop("form_list")
        self.initial_dict = kwargs.pop("initial_dict")
        super().__init__(**kwargs)

    def get_form(self, step=None, data=None, files=None):
        # active_company = get_active_company_from_session(self.request)
        if step is None:
            step = self.steps.current

        if step == "2":
            step1data = self.get_cleaned_data_for_step("1")
            if step1data is None:
                messages.warning(self.request, _("Please select at least 1 regulator"))

        return super().get_form(step, data, files)

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)

        context["steps"] = [
            _("Contact"),
            ("Competent authorities"),
            _("Regulations"),
            _("Sectors"),
            _("Detection date"),
        ]
        context["action"] = "Create"

        return context

    def render_goto_step(self, goto_step, **kwargs):
        form1 = self.get_form(
            self.steps.current, data=self.request.POST, files=self.request.FILES
        )

        self.storage.set_step_data(self.steps.current, self.process_step(form1))
        self.storage.set_step_files(self.steps.current, self.process_step_files(form1))

        return super().render_goto_step(goto_step, **kwargs)

    def get_form_initial(self, step):
        if step == "2":
            step1data = self.get_cleaned_data_for_step("1")
            if step1data:
                ids = step1data.get("regulators", "")
                regulators = Regulator.objects.filter(id__in=ids)
                return self.initial_dict.get(step, {"regulators": regulators})
        if step == "3":
            step2data = self.get_cleaned_data_for_step("2")
            step1data = self.get_cleaned_data_for_step("1")
            if step2data:
                ids = step2data.get("regulations", "")
                regulations = Regulation.objects.filter(id__in=ids)
                ids = step1data.get("regulators", "")
                regulators = Regulator.objects.filter(id__in=ids)
                return self.initial_dict.get(
                    step, {"regulations": regulations, "regulators": regulators}
                )
        return self.initial_dict.get(step, {})

    def done(self, form_list, **kwargs):
        if is_incidents_report_limit_reached(self.request):
            return HttpResponseRedirect("/incidents")

        user = self.request.user
        data = self.get_all_cleaned_data()
        company = get_active_company_from_session(self.request)
        sectors_id = extract_ids(data.get("sectors", []))
        regulators_id = extract_ids(data.get("regulators", []))
        regulations_id = extract_ids(data.get("regulations", []))

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
                company_name=company.name if company else data.get("company_name"),
                sector_regulation=sector_regulation,
                incident_timezone=data.get("incident_timezone", TIME_ZONE),
                incident_detection_date=incident_detection_date,
            )
            if incident:
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
                number_of_incident = f"{incidents_per_company:04}"
                incident.incident_id = (
                    f"{company_for_ref}_{sector_for_ref}_{subsector_for_ref}_"
                    f"{number_of_incident}_{date.today().year}"
                )

                incident.save()

                create_entry_log(user, incident, None, "COMMENT")

                # send The email notification opening
                if sector_regulation.opening_email is not None:
                    send_email(sector_regulation.opening_email, incident)

        return HttpResponseRedirect("/incidents")


class WorkflowWizardView(SessionWizardView):
    """Wizard to manage the different workflows."""

    template_name = "declaration.html"
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

        if self.request.incident_workflow:
            self.incident_workflow = IncidentWorkflow.objects.get(
                pk=self.request.incident_workflow
            )
            self.incident = self.incident_workflow.incident
            self.workflow = self.incident_workflow.workflow
            if position == 0:
                kwargs.update({"instance": self.incident})
            # Regulator case
            elif (
                position == len(self.form_list) - 2
                and self.workflow.is_impact_needed
                and is_user_regulator(user)
            ):
                kwargs.update({"incident": self.incident})
            elif position == len(self.form_list) - 1 and is_user_regulator(user):
                kwargs.update({"instance": self.incident_workflow})
            # Operator case
            elif (
                position == len(self.form_list) - 1
                and self.workflow.is_impact_needed
                and not is_user_regulator(user)
            ):
                kwargs.update({"incident": self.incident})
            else:
                # regulator pass directly the incident_workflow
                kwargs.update(
                    {
                        "position": position - 1,
                        "incident_workflow": self.incident_workflow,
                    }
                )
        elif self.request.incident:
            self.incident = Incident.objects.get(pk=self.request.incident)
            if not self.request.workflow:
                self.workflow = self.incident.get_next_step()
            else:
                self.workflow = self.request.workflow

            if position == 0:
                kwargs.update({"instance": self.incident})
            elif position == len(self.form_list) - 1 and self.workflow.is_impact_needed:
                kwargs.update({"incident": self.incident})
            else:
                kwargs.update(
                    {
                        "position": position - 1,
                        "workflow": self.workflow,
                        "incident": self.incident,
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
                    user, incident_workflow.incident, incident_workflow, "READ"
                )

        return super().get(self, request, *args, **kwargs)

    def get_form(self, step=None, data=None, files=None):
        if step is None:
            step = self.steps.current
        position = int(step)
        user = self.request.user
        # Operator : Complete an existing workflow or see historic
        # Regulator : See the report
        form = super().get_form(step=step, data=data, files=files)

        # Read only for regulator except for last form (save comment)
        # Read only for operator review (read_only = True)
        if self.read_only:
            last_form_index = -1
        else:
            last_form_index = len(self.form_list) - 1
        if (is_user_regulator(user) and position != last_form_index) or self.read_only:
            for field in form.fields:
                form.fields[field].disabled = True
                form.fields[field].required = False
                # replace following widget by more readable in read only
                if (
                    form.fields[field].widget.__class__.__name__
                    == "DropdownCheckboxSelectMultiple"
                ):
                    initial = ""
                    COUNTRY_DICT = dict(countries)
                    REGIONAL_DICT = dict(REGIONAL_AREA)
                    for val in form.fields[field].initial:
                        if val != "":
                            if val in COUNTRY_DICT:
                                initial = initial + COUNTRY_DICT[val] + " - "
                            elif val in REGIONAL_DICT:
                                initial = initial + REGIONAL_DICT[val] + " - "
                            else:
                                initial = initial + val + " - "
                    new_field = forms.CharField(
                        required=False,
                        disabled=True,
                        label=form.fields[field].label,
                        initial=initial,
                    )
                    form.fields[field] = new_field

        return form

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)

        if self.workflow is not None:
            context["action"] = "Edit"
            context["steps"] = []
            questions = self.workflow.questions
            categories = set()
            for question in questions.all():
                categories.add(question.category)
            categ_list = []
            for category in categories:
                categ_list.append(category)
            categ_list.sort(key=lambda c: c.position)

            context["steps"].append(_("Timeline"))
            context["steps"] += categ_list
            if self.workflow.is_impact_needed:
                context["steps"].append(_("Impacts"))

            user = self.request.user
            if is_user_regulator(user):
                context["steps"].append(_("Comment"))
        return context

    def render_goto_step(self, goto_step, **kwargs):
        current_step = self.steps.current
        form = self.get_form(
            current_step, data=self.request.POST, files=self.request.FILES
        )

        if form.is_valid():
            self.storage.set_step_data(current_step, self.process_step(form))
            self.storage.set_step_files(current_step, self.process_step_files(form))

        return super().render_goto_step(goto_step, **kwargs)

    def done(self, form_list, **kwargs):
        user = self.request.user
        data = self.get_all_cleaned_data()
        if not is_user_regulator(user) and not self.read_only:
            incident_timezone = data.get("incident_timezone", TIME_ZONE)
            incident_starting_date = data.get("incident_starting_date", None)
            incident_detection_date = data.get("incident_detection_date", None)
            local_tz = pytz.timezone(incident_timezone)
            email = self.workflow.submission_email or None
            self.incident = self.incident or get_object_or_404(
                Incident, pk=self.request.incident
            )
            self.incident.review_status = "DELIV"
            self.incident.incident_timezone = incident_timezone

            if incident_starting_date:
                self.incident.incident_starting_date = convert_to_utc(
                    incident_starting_date, local_tz
                )

            if (
                incident_detection_date
                and not self.incident.sector_regulation.is_detection_date_needed
            ):
                self.incident.incident_detection_date = convert_to_utc(
                    incident_detection_date, local_tz
                )

            self.incident.save()
            # manage question
            incident_workflow = save_answers(data, self.incident, self.workflow)
            create_entry_log(user, self.incident, incident_workflow, "CREATE")

            if email:
                send_email(email, self.incident)
        # save the comment if the user is regulator
        elif is_user_regulator(user) and not self.read_only:
            incident_workflow = (
                IncidentWorkflow.objects.all()
                .filter(incident=self.incident, workflow=self.workflow)
                .order_by("-timestamp")
                .first()
            )
            incident_workflow.comment = data.get("comment", None)
            incident_workflow.save()
            create_entry_log(
                user, incident_workflow.incident, incident_workflow, "COMMENT"
            )

        return HttpResponseRedirect("/incidents")


def save_answers(data=None, incident=None, workflow=None):
    """Save the answers."""
    prefix = "__question__"
    questions_data = {
        key[slice(len(prefix), None)]: value
        for key, value in data.items()
        if key.startswith(prefix)
    }

    # We create a new incident workflow in all the case (history)
    incident_workflow = IncidentWorkflow.objects.create(
        incident=incident, workflow=workflow
    )
    incident_workflow.review_status = "DELIV"
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
            question = Question.objects.get(pk=key)
            if question.question_type == "FREETEXT":
                answer = value
            elif question.question_type == "DATE":
                if value:
                    answer = value.strftime("%Y-%m-%d %H:%M")
                else:
                    answer = None
            elif question.question_type == "CL" or question.question_type == "RL":
                answer = ""
                for val in value:
                    answer += val + ","
                answer = answer
            else:  # MULTI
                for val in value:
                    predefined_answers.append(PredefinedAnswer.objects.get(pk=val))
                answer = None
                if questions_data.get(key + "_answer", None):
                    answer = questions_data.get(key + "_answer")
            answer_object = Answer.objects.create(
                incident_workflow=incident_workflow,
                question=question,
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


def create_entry_log(user, incident, incident_report, action):
    log = LogReportRead.objects.create(
        user=user,
        incident=incident,
        incident_report=incident_report,
        action=action,
    )
    log.save()

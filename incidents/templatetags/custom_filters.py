import json
import math

from django import template
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone
from django.utils.translation import gettext as _

from incidents.models import IncidentWorkflow, SectorRegulationWorkflow

register = template.Library()


@register.filter
def get_class_name(value):
    return value.__class__.__name__


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter(name="split")
def split(value, key):
    return value.split(key)


@register.filter
def index(indexable, i):
    return indexable[int(i)]


@register.filter()
def translate(text):
    return _(text)


@register.simple_tag
def get_report_tooltip(value):
    if value == "report-pass":
        return _("The report has passed the review.")
    elif value == "report-fail":
        return _("The report has failed the review.")
    elif value == "report-under-review":
        return _("The report is currently under review.")
    elif value == "report-late-under-review":
        return _("The report is currently under review.")
    elif value == "report-overdue":
        return _("The submission of the report is overdue.")
    else:
        return _("The report has not been submitted yet.")


@register.filter
def get_report_class(value, incident=None):
    if incident and not isinstance(value, str):
        value = is_deadline_exceeded(value, incident)
    if value == "PASS":
        return "report-pass"
    elif value == "FAIL":
        return "report-fail"
    elif value == "DELIV":
        return "report-under-review"
    elif value == "OUT":
        return "report-overdue"
    elif value == "LATE":
        return "report-late-under-review"
    else:
        return "report-unsubmitted"


@register.filter
def filter_workflows(incidentWorkflows, report_id):
    for incidentworkflow in incidentWorkflows:
        if incidentworkflow.workflow.pk == report_id:
            return incidentworkflow
    return None


# return the incident workflow with form and be sure it's the last one
@register.filter
def filter_workflows_forms(incident, report):
    latest_incident_workflow = incident.get_latest_incident_workflow_by_workflow(report)
    if latest_incident_workflow is not None:
        latest_incident_workflow_id = latest_incident_workflow.id
    report_id = report.id
    incidentWorkflows_forms = incident.formsWorkflow
    for incidentworkflow in incidentWorkflows_forms:
        if latest_incident_workflow is not None:
            if (
                incidentworkflow.instance.workflow.pk == report_id
                and incidentworkflow.instance.id == latest_incident_workflow_id
            ):
                return incidentworkflow
        else:
            if incidentworkflow.instance.workflow.pk == report_id:
                return incidentworkflow
    return None


@register.simple_tag
def is_workflow_disabled(allWorkflows, incidentWorkflows, report):
    current_index = allWorkflows.index(report)

    if not incidentWorkflows and not current_index == 0:
        return True

    workflow_list = [workflow.workflow for workflow in incidentWorkflows]

    if (
        current_index < len(allWorkflows) - 1
        and allWorkflows[current_index + 1] in workflow_list
    ):
        return True

    if (
        current_index < len(allWorkflows) - 1
        and current_index > 1
        and allWorkflows[current_index - 1] not in workflow_list
    ):
        return True

    if (
        len(allWorkflows) > 1
        and current_index == len(allWorkflows) - 1
        and allWorkflows[current_index - 1] not in workflow_list
    ):
        return True

    return False


@register.simple_tag
def is_deadline_exceeded(report, incident):
    latest_incident_workflow = incident.get_latest_incident_workflow_by_workflow(report)

    if latest_incident_workflow is not None:
        return latest_incident_workflow.review_status
    if incident is not None and report is not None:
        sr_workflow = (
            SectorRegulationWorkflow.objects.all()
            .filter(
                sector_regulation=incident.sector_regulation,
                workflow=report,
            )
            .first()
        )
        actual_time = timezone.now()
        if sr_workflow.trigger_event_before_deadline == "DETECT_DATE":
            if incident.incident_detection_date is not None:
                dt = actual_time - incident.incident_detection_date
                if (
                    math.floor(dt.total_seconds() / 60 / 60)
                    >= sr_workflow.delay_in_hours_before_deadline
                ):
                    return "OUT"
        elif sr_workflow.trigger_event_before_deadline == "NOTIF_DATE":
            dt = actual_time - incident.incident_notification_date
            if (
                math.floor(dt.total_seconds() / 60 / 60)
                >= sr_workflow.delay_in_hours_before_deadline
            ):
                return "OUT"
        elif (
            sr_workflow.trigger_event_before_deadline == "PREV_WORK"
            and incident.get_previous_workflow(report) is not False
        ):
            previous_workflow = incident.get_previous_workflow(report)
            previous_incident_workflow = (
                IncidentWorkflow.objects.all()
                .filter(incident=incident, workflow=previous_workflow.workflow)
                .order_by("-timestamp")
                .first()
            )
            if previous_incident_workflow is not None:
                dt = actual_time - previous_incident_workflow.timestamp
                if (
                    math.floor(dt.total_seconds() / 60 / 60)
                    >= sr_workflow.delay_in_hours_before_deadline
                ):
                    return "OUT"

    return "UNDE"


# get the incident workflow by workflow and incident to see the historic for operator
@register.filter
def get_incident_workflow_by_workflow(incident, workflow):
    queryset = (
        IncidentWorkflow.objects.all()
        .filter(incident=incident, workflow=workflow)
        .order_by("-timestamp")
    )

    if not queryset:
        return None

    data = list(queryset.values("id", "timestamp"))
    for item in data:
        item["timestamp"] = item["timestamp"].isoformat()

    return json.dumps(data, cls=DjangoJSONEncoder)


# get settings value
@register.simple_tag
def settings_value(name):
    return getattr(settings, name, "")


@register.filter
def range_list(value):
    return range(1, int(value) + 1)

from django import template
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


@register.filter
def index(indexable, i):
    return indexable[int(i)]


@register.filter()
def translate(text):
    return _(text)


@register.simple_tag
def status_class(value):
    if value == "PASS":
        return "table-success"
    elif value == "FAIL":
        return "table-danger"
    elif value == "DELIV":
        return "table-info"
    elif value == "OUT":
        return "table-secondary"
    else:
        return "table-secondary"


@register.filter
def filter_workflows(incidentWorkflows, report_id):
    for incidentworkflow in incidentWorkflows:
        if incidentworkflow.workflow.pk == report_id:
            return incidentworkflow
    return None


@register.filter
def filter_workflows_forms(incidentWorkflows_forms, report_id):
    for incidentworkflow in incidentWorkflows_forms:
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
        len(allWorkflows) > 1
        and current_index == len(allWorkflows) - 1
        and allWorkflows[current_index - 1] not in workflow_list
    ):
        return True

    return False


@register.simple_tag
def is_deadline_exceeded(report, incident):
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
                    round(dt.seconds / 60 / 60, 0)
                    >= sr_workflow.delay_in_hours_before_deadline
                ):
                    incident.review_status = "OUT"
                    return _("Not delivered and deadline exceeded")
        elif sr_workflow.trigger_event_before_deadline == "NOTIF_DATE":
            dt = actual_time - incident.notification_date
            if (
                round(dt.seconds / 60 / 60, 0)
                >= sr_workflow.delay_in_hours_before_deadline
            ):
                incident.review_status = "OUT"
                return _("Not delivered and deadline exceeded")
        elif (
            sr_workflow.trigger_event_before_deadline == "PREV_WORK"
            and incident.get_previous_workflow(report) is not None
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
                    round(dt.seconds / 60 / 60, 0)
                    >= sr_workflow.delay_in_hours_before_deadline
                ):
                    incident.review_status = "OUT"
                    return _("Not delivered and deadline exceeded")

    return _("Not delivered")

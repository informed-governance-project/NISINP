import math

from django.utils import timezone

from .models import IncidentWorkflow, SectorRegulationWorkflow


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

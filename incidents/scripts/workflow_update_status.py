import logging
import math

from django.utils import timezone

from incidents.email import send_email
from incidents.models import Incident, IncidentWorkflow, SectorRegulationWorkflow

logger = logging.getLogger(__name__)


# Script to run every hour
def run(logger=logger):
    logger.info("running workflow_update_status.py")
    # for all unclosed incident
    actual_time = timezone.now()
    ongoing_incidents = Incident.objects.filter(incident_status="GOING")
    for incident in ongoing_incidents:
        incident_workflows = incident.get_latest_incident_workflows().exclude(
            review_status__in=["PASS", "OUT"]
        )
        for incident_workflow in incident_workflows:
            sector_regulation_workflow = SectorRegulationWorkflow.objects.filter(
                sector_regulation=incident.sector_regulation,
                workflow=incident_workflow.workflow,
            ).first()

            if not sector_regulation_workflow:
                continue

            trigger_event = sector_regulation_workflow.trigger_event_before_deadline
            delay_in_hours = sector_regulation_workflow.delay_in_hours_before_deadline

            # check notif date
            if trigger_event == "NOTIF_DATE":
                dt = actual_time - incident_workflow.timestamp

            # detection date
            elif (
                trigger_event == "DETECT_DATE"
                and incident.incident_detection_date is not None
            ):
                dt = actual_time - incident.incident_detection_date

            # previous incident_workflow
            elif trigger_event == "PREV_WORK":
                prev_workflow = incident_workflow.get_previous_workflow()
                if not prev_workflow:
                    continue

                previous_incident_workflow = (
                    IncidentWorkflow.objects.filter(
                        incident=incident,
                        workflow=prev_workflow,
                    )
                    .order_by("-timestamp")
                    .first()
                )
                if not previous_incident_workflow:
                    continue

                dt = actual_time - previous_incident_workflow.timestamp
            else:
                continue

            if dt and math.floor(dt.total_seconds() / 60 / 60) >= delay_in_hours:
                incident_workflow.review_status = "OUT"
                incident_workflow.save()
                send_email(
                    incident.sector_regulation.report_status_changed_email,
                    incident,
                )

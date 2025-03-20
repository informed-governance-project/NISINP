import logging
import math

from django.utils import timezone

from incidents.email import send_email
from incidents.models import Incident, IncidentWorkflow, SectorRegulationWorkflow

logger = logging.getLogger(__name__)


# Script to run every hour
# Send an email when the delay is overdue
# The status change is managed in frontend
def run(logger=logger):
    logger.info("running workflow_update_status.py")
    # for all unclosed incident
    actual_time = timezone.now()
    ongoing_incidents = Incident.objects.filter(incident_status="GOING")
    for incident in ongoing_incidents:
        filled_workflow_ids = IncidentWorkflow.objects.filter(incident=incident).values_list("workflow", flat=True)
        unfilled_report_ids = incident.sector_regulation.workflows.exclude(
            id__in=filled_workflow_ids
        ).values_list("id", flat=True)
        srw = SectorRegulationWorkflow.objects.filter(
            workflow__in=unfilled_report_ids,
            sector_regulation=incident.sector_regulation,
        )
        for report in srw:
            trigger_event = report.trigger_event_before_deadline
            delay_in_hours = report.delay_in_hours_before_deadline

            # check notif date
            if trigger_event == "NOTIF_DATE":
                dt = actual_time - incident.incident_notification_date

            # detection date
            elif (
                trigger_event == "DETECT_DATE"
                and incident.incident_detection_date is not None
            ):
                dt = actual_time - incident.incident_detection_date

            # previous incident_workflow
            elif trigger_event == "PREV_WORK":
                prev_workflow = report.get_previous_report()
                if not prev_workflow:
                    continue

                previous_incident_workflow = (
                    IncidentWorkflow.objects.filter(
                        incident=incident,
                        workflow=prev_workflow.workflow,
                    )
                    .order_by("-timestamp")
                    .first()
                )
                if not previous_incident_workflow:
                    continue

                dt = actual_time - previous_incident_workflow.timestamp
            else:
                continue

            if dt and math.floor(dt.total_seconds() / 60 / 60) == delay_in_hours:
                if incident.sector_regulation.report_status_changed_email:
                    send_email(
                        incident.sector_regulation.report_status_changed_email,
                        incident,
                    )

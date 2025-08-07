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
        if incident.sector_regulation is not None:
            unfilled_report_ids = incident.sector_regulation.workflows.exclude(
                id__in=filled_workflow_ids
            ).values_list("id", flat=True)
            srw = SectorRegulationWorkflow.objects.filter(
                workflow__in=unfilled_report_ids,
                sector_regulation=incident.sector_regulation,
            )
            for report in srw:
                delay_in_hours = report.delay_in_hours_before_deadline

                dt = report.how_late_is_the_report(incident, actual_time)

                if dt and math.floor(dt.total_seconds() / 60 / 60) == delay_in_hours:
                    if incident.sector_regulation.report_status_changed_email:
                        send_email(
                            incident.sector_regulation.report_status_changed_email,
                            incident,
                        )

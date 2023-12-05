from django.utils import timezone

from incidents.models import Incident, SectorRegulationWorkflow


# Script to run every hour
def run():
    # for all unclosed incident
    actual_time = timezone.now()
    for incident in Incident.objects.filter(incident_status="GOING"):
        # Workflow with deadline from prev workflow
        for incident_workflow in incident.get_latest_incident_workflows():
            # check status
            if incident_workflow.review_status != "PASS":
                sector_regulation_workflow = SectorRegulationWorkflow.objects.all().filter(
                        sector_regulation=incident.sector_regulation,
                        workflow=incident_workflow.workflow
                ).first()
                # check notif date
                if sector_regulation_workflow.trigger_event_before_deadline == "NOTIF_DATE":
                    dt = actual_time - incident_workflow.timestamp
                    if round(dt.seconds/60/60, 0) == sector_regulation_workflow.delay_in_hours_before_deadline:
                        incident_workflow.review_status = "OUT"
                # detection date
                elif sector_regulation_workflow.trigger_event_before_deadline == "DETECT_DATE":
                    if incident.incident_detection_date is not None:
                        dt = actual_time - incident.incident_detection_date
                        if round(dt.seconds/60/60, 0) == sector_regulation_workflow.delay_in_hours_before_deadline:
                            incident_workflow.review_status = "OUT"
                # previous incident_workflow
                elif sector_regulation_workflow.trigger_event_before_deadline == "PREV_WORK":
                    prev_work = incident_workflow.get_previous_workflow()
                    if prev_work is not False:
                        dt = actual_time - prev_work.timestamp
                        if round(dt.seconds/60/60, 0) == sector_regulation_workflow.delay_in_hours_before_deadline:
                            incident_workflow.review_status = "OUT"

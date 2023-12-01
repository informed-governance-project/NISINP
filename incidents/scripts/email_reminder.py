from django.utils import timezone

from incidents.email import send_email
from incidents.models import Incident, IncidentWorkflow, SectorRegulationWorkflowEmail, SectorRegulationWorkflow


# Script to run every hour
def run():
    # for all unclosed incident
    actual_time = timezone.now()
    for incident in Incident.objects.filter(incident_status="GOING"):
        # Workflow with deadline from prev workflow
        for incident_workflow in incident.get_latest_incident_workflows():
            # chek if there is a next workflow
            next_workflow = incident_workflow.get_next_workflow()
            if next_workflow is not False:
                next_incident_workflow = IncidentWorkflow.objects.all().filter(
                    incident=incident,
                    workflow=next_workflow,
                ).order_by("-timestamp").first()
                # there is one next workflow but not filled
                if next_incident_workflow is None:
                    next_sector_regulation_workflow = SectorRegulationWorkflow.objects.all().filter(
                        sector_regulation=incident.sector_regulation,
                        workflow=next_workflow
                    ).first()
                    emails = SectorRegulationWorkflowEmail.objects.all().filter(
                        sector_regulation_workflow=next_sector_regulation_workflow,
                        trigger_event="PREV_WORK"
                    )
                    for email in emails:
                        dt = actual_time - incident_workflow.timestamp
                        if round(dt.seconds/60/60, 0) == email.delay_in_hours:
                            send_email(email.email, incident)

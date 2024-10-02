from datetime import timedelta
from django.db.models.functions import Now
from governanceplatform.settings import INCIDENT_RETENTION_TIME_IN_DAY
from incidents.models import Incident


# Script to run once day
# remove incidents after a period configured in config.py
def run():
    # for all closed incident
    incident_to_delete_qs = Incident.objects.filter(
        incident_status='CLOSE',
        incident_notification_date__lte=Now()-timedelta(days=INCIDENT_RETENTION_TIME_IN_DAY)
    )
    incident_to_delete_qs.delete()

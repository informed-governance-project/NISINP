from datetime import timedelta
from django.db.models.functions import Now
from governanceplatform.settings import LOG_RETENTION_TIME_IN_DAY
from django.contrib.admin.models import LogEntry


# Script to run once day
# remove log after a period configured in config.py
def run():
    log_to_delete = LogEntry.objects.filter(action_time__lte=Now()-timedelta(days=LOG_RETENTION_TIME_IN_DAY))
    log_to_delete.delete()

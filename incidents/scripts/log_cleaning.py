from datetime import timedelta
from django.db.models.functions import Now
from governanceplatform.settings import LOG_RETENTION_TIME_IN_DAY
from django.contrib.admin.models import LogEntry
from governanceplatform.models import ScriptLogEntry

import logging

# Script to run once day
# remove log after a period configured in config.py
def run(logger=logging.getLogger(__name__)):
    logger.info("running log_cleaning.py")
    log_to_delete = LogEntry.objects.filter(action_time__lte=Now()-timedelta(days=LOG_RETENTION_TIME_IN_DAY))
    ScriptLogEntry.objects.create(
        object_id=None,
        object_repr="System:Log script deletion " + str(log_to_delete.count()) + " log(s) deleted",
        action_flag=3,
    )
    log_to_delete.delete()

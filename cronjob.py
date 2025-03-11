#!/usr/bin/env python3

import datetime
import logging
import os
import time
from traceback import format_exc

import django
import schedule

from incidents.scripts import (
    email_reminder,
    incident_cleaning,
    log_cleaning,
    workflow_update_status,
)

# django init
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "governanceplatform.settings")
django.setup()

logger = logging.getLogger(__name__)


# check https://schedule.readthedocs.io/en/stable/ for usage
# some jobs do not have full exception handling
class SafeScheduler(schedule.Scheduler):
    def __init__(self, reschedule_on_failure=True):
        self.reschedule_on_failure = reschedule_on_failure
        super().__init__()

    def _run_job(self, job):
        try:
            super()._run_job(job)
        except Exception:
            logger.error(format_exc())
            job.last_run = datetime.datetime.now()
            job._schedule_next_run()


scheduler = SafeScheduler()

# jobs definition
email_reminder.run()
incident_cleaning.run()
log_cleaning.run()
workflow_update_status.run()

scheduler.every().hour.do(email_reminder.run)
scheduler.every().day.at("20:30").do(incident_cleaning.run)
scheduler.every().day.at("21:00").do(log_cleaning.run)
scheduler.every().hour.do(workflow_update_status.run)

# endless scheduler loop
while True:
    scheduler.run_pending()
    time.sleep(1)

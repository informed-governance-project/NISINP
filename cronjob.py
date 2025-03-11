#!/usr/bin/env python3

import time
import datetime

# django init
import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "governanceplatform.settings")
django.setup()

import logging
logger = logging.getLogger(__name__)
from traceback import format_exc

import schedule
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
import incidents.scripts.email_reminder
incidents.scripts.email_reminder.run()
scheduler.every().hour.do(incidents.scripts.email_reminder.run)

import incidents.scripts.incident_cleaning
incidents.scripts.incident_cleaning.run()
scheduler.every().day.at("20:30").do(incidents.scripts.incident_cleaning.run)

import incidents.scripts.log_cleaning
incidents.scripts.log_cleaning.run()
scheduler.every().day.at("21:00").do(incidents.scripts.log_cleaning.run)

import incidents.scripts.workflow_update_status
incidents.scripts.workflow_update_status.run()
scheduler.every().hour.do(incidents.scripts.workflow_update_status.run)

# endless scheduler loop
while True:
    scheduler.run_pending()
    time.sleep(1)

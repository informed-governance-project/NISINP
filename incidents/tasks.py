#!/usr/bin/env python3

import logging  # noqa: F401
import os

import django

# django init
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "governanceplatform.settings")
django.setup()

from incidents.scripts import (  # noqa: F401, E402
    email_reminder,
    incident_cleaning,
    log_cleaning,
    workflow_update_status,
)

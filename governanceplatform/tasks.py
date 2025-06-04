#!/usr/bin/env python3

import logging
import os

import django

# django init
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "governanceplatform.settings")
django.setup()

from governanceplatform.scripts import (  # noqa: E402
    unactive_account_cleaning,
    update_all_group_permissions,
)

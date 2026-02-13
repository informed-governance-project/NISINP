#!/usr/bin/env python3

import os

import django

# django init
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "governanceplatform.settings")
django.setup()

from securityobjectives.scripts import so_declarations_cleaning  # noqa: E402 F401

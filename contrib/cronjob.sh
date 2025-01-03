#!/usr/bin/env bash

set -eu

error=0

./manage.py runscript log_cleaning || error=1
./manage.py runscript incident_cleaning || error=1
./manage.py runscript workflow_update_status || error=1
./manage.py runscript email_reminder || error=1

exit "$error"

#!/usr/bin/env bash

set -euo pipefail

python manage.py collectstatic
python manage.py migrate
python manage.py compilemessages

exec gunicorn governanceplatform.wsgi --workers "$APP_WORKERS" --bind "0.0.0.0:$APP_PORT"

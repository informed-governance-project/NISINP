#!/usr/bin/env bash

set -euo pipefail

python manage.py collectstatic --noinput > /dev/null
python manage.py migrate
python manage.py compilemessages

exec gunicorn governanceplatform.wsgi --workers "$APP_WORKERS" --bind "$APP_BIND_ADDRESS:$APP_PORT"

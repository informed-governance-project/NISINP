#!/usr/bin/env bash

set -euo pipefail

python manage.py collectstatic
python manage.py migrate
python manage.py compilemessages

exec python manage.py runserver 0.0.0.0:8888 --insecure

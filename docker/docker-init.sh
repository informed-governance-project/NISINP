#!/bin/bash

set -euo pipefail

docker_init_d=/docker-init.d
if [ -d $docker_init_d -a $docker_init_d/*.sh != "${docker_init_d}/*.sh" ]; then
    for f in $docker_init_d/*.sh; do
        source "$f"
    done
fi

python manage.py collectstatic --noinput > /dev/null
python manage.py migrate
python manage.py compilemessages

exec gunicorn governanceplatform.wsgi --workers "$APP_WORKERS" --bind "$APP_BIND_ADDRESS:$APP_PORT"

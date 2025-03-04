# Install and run via Docker

Re-use the `docker/docker-compose.example.yml` and create the volumes directory
(see below)

## Database

See main README for configuration, currently the container is started in host
network mode to ease database and MTA/mail access

## Volumes

> Please note that the container runs as user `www-data` (uid **33**), so at
> least the `theme`, `static` and `logs` volumes **need** to be owned by
> `www-data` (uid **33**)

There are four volumes to setup:

- `/app/governanceplatform/config.py`  
  The application configuration, based on `governanceplatform/config_dev.py`

- `/app/governanceplatform/theme`  
  The theme directory, currently by default based on
  `github.com/informed-governance-project/default-theme`, that may change in the
  future or if you wish to use a custom theme for your needs.
  This directory needs to be writable as translation files (.po) are written
  there at application start up. Most of the time specific version of this
  application will require specific version of the theme - please ask your
  theme developper which theme version you should use.

- `/app/governanceplatform/static`  
  A writable directory where Django can collect static assets, this directory
  should be served by your reverse proxy/web server (see
  `docker/apache2-example.conf` for an reverse proxy configuration example)

- `/app/governanceplatform/logs`  
  A writable location for logs (if you configure logging through files)

## Startup scripts

Any `*.sh` script found under `/docker-init.d/` will be *sourced* before the
various static assets generation, Django migration etc ... this directory can
be exposed as a Docker volume also.

This allows application deployers to inject/fix anything they deem necessary
before the actual Django runtime init and application startup.

## Startup

`NISINP_VERSION=vX.Y.Z docker-compose up -d`

- `NISINP_VERSION`: which tag to deploy
- `NISINP_IMAGE`: container image path (without version) (defaults to `ghcr.io/informed-governance-project/nisinp`)
- `APP_PORT`: which port to bind to (defaults to `8888`)
- `APP_BIND_ADDRESSS`: which address to bind to (defaults to `127.0.0.1`)

## Scheduled tasks

A contrib script is included in the built docker image in `/app/cronjob.sh`,
you should configure this script to be executed every minute by a cronjob or systemd timer.

`docker exec governanceplatform /app/cronjob.sh`

Exit code will be `1` if any of the task fails

## Reverse proxy configuration

Static assets are served directly by a web server/reverse proxy and not by the
Gunicorn python runtime

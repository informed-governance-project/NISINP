# Install and run via Docker

Re-use the `docker/docker-compose.example.yml` and create the volumes directory
(see below)

## Database

See main README for configuration, the container is not started in host
network mode anymore and `postgres` is now part of `docker-compose.yml`.

## Volumes

> Please note that the container runs as user `www-data` (uid **33**), so at
> least the `theme` and, if used, `logs` volumes **need** to be owned by
> `www-data` (uid **33**)

There are now only two mandatory volumes to setup:

- `/app/governanceplatform/config.py`  
  The application configuration, based on `governanceplatform/config_dev.py`

- `/app/theme`  
  The theme directory, currently by default based on
  `github.com/informed-governance-project/default-theme`, that may change in the
  future or if you wish to use a custom theme for your needs.
  This directory needs to be writable as translation files (.po) are written
  there at application start up. Most of the time specific version of this
  application will require specific version of the theme - please ask your
  theme developper which theme version you should use.


## Logging configuration

If you want to use a pure stdout based logging (no `django.log` file), the
following configuration excerpt may be useful.

```
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "root": {"level": "INFO", "handlers": ["console"]},
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "stream": sys.stdout,
            "formatter": "app",
        },
    },
    "formatters": {
        "app": {
            "format": (
                "[%(asctime)s] [%(levelname)-8s] (%(module)s.%(funcName)s) %(message)s"
            ),
            "datefmt": "%Y-%m-%d %H:%M:%S %z",
        },
    },
}
```

## Database configuration

To setup your `postgres` credentials in the Django application from environment
variables you may use the following piece of configuration (check
`docker-compose.yml` for example).

```
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "serima-governance"),
        "USER": os.getenv("POSTGRES_USER", "<user>"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "<password>"),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": int(os.getenv("POSTGRES_PORT", 5432)),
    },
}
```

## Startup scripts

Any `*.sh` script found under `/docker-init.d/` will be *sourced* before the
various static assets generation, Django migration etc ... this directory can
be exposed as a Docker volume also.

This allows application deployers to inject/fix anything they deem necessary
before the actual Django runtime init and application startup.

## Startup

`NISINP_VERSION=vX.Y.Z NISINP_ENVIRONMENT=prod docker-compose up -d`

- `NISINP_VERSION`: which tag to deploy
- `NISINP_IMAGE`: container image path (without version) (defaults to `ghcr.io/informed-governance-project/nisinp`)
- `NISINP_ENVIRONMENT`: identifier for your environment, mainly for container naming
- `APP_PORT`: which port to bind to (defaults to `8888`)
- `APP_BIND_ADDRESSS`: which address to bind to (defaults to `0.0.0.0`)

## Reverse proxy configuration

Static assets are handled by the Python `whitenoise` module that registers a handler to
serve static assets directly from the Python runtime.

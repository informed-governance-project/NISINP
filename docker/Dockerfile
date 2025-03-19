FROM node:18-bullseye AS npmbuilder

WORKDIR /app

COPY package.json /app
COPY package-lock.json /app

RUN npm ci
RUN npm install

FROM python:3.11-bullseye

ARG APP_VERSION
ARG GUNICORN_VERSION=23.0
ARG MULTIRUN_VERSION=1.1.3
ENV APP_VERSION=$APP_VERSION

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
  gettext \
  && rm -rf /var/lib/apt/lists/*

RUN wget -c https://github.com/nicolas-van/multirun/releases/download/${MULTIRUN_VERSION}/multirun-x86_64-linux-gnu-${MULTIRUN_VERSION}.tar.gz -O - | tar -C /bin -xz

# running as www-data, we need homedir and PATH for --user installed pip modules
RUN mkdir -p /app /var/www && chown www-data: /app /var/www
ENV PATH="${PATH}:/var/www/.local/bin"
USER www-data

# because package.json scripts.postinstall tries to be smart
COPY --chown=www-data --from=npmbuilder /app/node_modules /app/static/npm_components

COPY --chown=www-data governanceplatform /app/governanceplatform
COPY --chown=www-data incidents /app/incidents
COPY --chown=www-data locale /app/locale
COPY --chown=www-data static /app/static
COPY --chown=www-data templates /app/templates

COPY --chown=www-data pyproject.toml /app/pyproject.toml
COPY --chown=www-data README.md /app/README.md
COPY --chown=www-data manage.py /app/manage.py

RUN python3 -m pip install --user .
RUN python3 -m pip install --user gunicorn~=$GUNICORN_VERSION

COPY cronjob.py /app/cronjob.py
COPY docker/docker-init.sh /app/docker-init.sh

ENTRYPOINT [ "/app/docker-init.sh" ]

ENV APP_PORT="8888"
ENV APP_BIND_ADDRESS="0.0.0.0"
ENV APP_WORKERS="4"

EXPOSE $APP_PORT

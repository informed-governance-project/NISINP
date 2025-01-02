FROM node:18-bullseye AS npmbuilder

WORKDIR /app

COPY package.json /app
COPY package-lock.json /app
COPY theme/static/scss/custom.scss /app/theme/static/scss/custom.scss

RUN npm ci
RUN npm install

FROM python:3.11-bullseye

ARG APP_VERSION
ENV APP_VERSION=$APP_VERSION

WORKDIR /app

# because package.json scripts.postinstall tries to be smart
COPY --from=npmbuilder /app/node_modules /app/static/npm_components
# and also package.json script.compile-scss
COPY --from=npmbuilder /app/theme/static/scss/custom.scss /app/theme/static/scss/custom.scss

COPY api /app/api
COPY governanceplatform /app/governanceplatform
COPY incidents /app/incidents
COPY locale /app/locale
COPY proxy /app/proxy
COPY static /app/static
COPY templates /app/templates
COPY theme /app/theme

COPY pyproject.toml /app/pyproject.toml
COPY README.md /app/README.md
COPY manage.py /app/manage.py

RUN mkdir -p /app/theme/static

RUN python -m pip install .

RUN apt-get update && apt-get install -y gettext && apt-get clean

COPY docker-init.sh /app/docker-init.sh
CMD /app/docker-init.sh

EXPOSE 8888

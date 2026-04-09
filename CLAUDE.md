# NISINP – Project Instructions

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Language | Python | ^3.12 |
| Framework | Django | ^5.2 |
| Database | PostgreSQL | - |
| Task Queue | Celery + Redis | ^5.5 / ^7.4 |
| Frontend | Bootstrap 5 + jQuery | - |
| PDF | WeasyPrint | ^68 |
| API | Django REST Framework + drf-spectacular | - |
| i18n | django-parler (4 languages: en/fr/nl/de) | ^2.3 |
| Auth | django-two-factor-auth + django-otp | - |
| Testing | pytest + pytest-django | - |

## Build & Run

```bash
# Install dependencies
poetry install

# Dev server
make run                   # python manage.py runserver

# Migrations
make migration             # makemigrations
make migrate               # migrate

# Collect static / compile messages
make update

# Tests
pytest

# Linting / formatting
black .
isort .
flake8 .
```

## Configuration

Settings are loaded from `governanceplatform/config.py` (not in VCS). Copy `governanceplatform/config_dev.py` as a starting point.

CI uses `DJANGO_CI=True` env var which falls back to `config_dev.py` automatically.

## Project Structure

```
governanceplatform/   → Django project root (settings, urls, auth, models)
  migrations/         → DB migrations for core models
  tests/              → Tests for platform views, models, admin, DB
  management/         → Custom management commands
  utils/              → Shared utilities
incidents/            → Main app: incident notification workflows
  migrations/         → DB migrations (50+ migrations)
  tests/              → Incident-specific tests
  scripts/            → Scheduled maintenance scripts
  pdf_generation.py   → PDF export via WeasyPrint
  email.py            → Email notifications
locale/               → Django translation files (en/fr/nl/de)
templates/            → Jinja/Django HTML templates
static/               → JS/CSS/images (npm-managed via Bootstrap 5)
docker/               → Dockerfile + docker-compose examples
docs/                 → Sphinx documentation + OpenAPI spec
```

## Conventions

- **Commit style**: `[scope]Description` (e.g. `[migrations]Added countries migrations`, `[docker]typo`)
- **Branches**: `dev` is the working branch; `master` is the release branch
- **Code formatting**: `black` + `isort` (profile=black) — enforced via pre-commit
- **Type checking**: `mypy` — configured in `pyproject.toml`
- **Test files**: `tests/test_*.py` pattern, using `pytest-django`
- **Test fixtures**: defined in per-app `tests/conftest.py`

## Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=. --cov-report=term-missing

# Single app
pytest governanceplatform/tests/
pytest incidents/tests/
```

Tests use `pytest-django` with PostgreSQL. The `DJANGO_CI=True` env var switches to `config_dev.py`.

## Key Entry Points

| What | Where |
|------|-------|
| URL routing | `governanceplatform/urls.py` → includes `incidents/urls.py` |
| Core models | `governanceplatform/models.py` |
| Incident models | `incidents/models.py` |
| Incident views | `incidents/views.py` |
| Platform views | `governanceplatform/views.py` |
| Settings | `governanceplatform/settings.py` + `config.py` |
| Celery tasks | `incidents/tasks.py`, `governanceplatform/tasks.py` |
| Admin | `governanceplatform/admin.py`, `incidents/admin.py` |
| API (optional) | Enabled via `API_ENABLED = True` in config; schema at `docs/_static/openapi.yml` |

## Where to Look

| I want to… | Look at… |
|------------|----------|
| Add an incident URL | `incidents/urls.py` |
| Add a platform URL | `governanceplatform/urls.py` |
| Add/modify a model | `incidents/models.py` or `governanceplatform/models.py` then `make migration` |
| Add a view | `incidents/views.py` or `governanceplatform/views.py` |
| Add a template | `templates/` |
| Add a translation string | Mark with `_()` then `make generatepot` |
| Run a scheduled task | `incidents/scripts/` + register in Celery |
| Change config | `governanceplatform/config.py` (not `config_dev.py`) |
| Build Docker image | `make image` |

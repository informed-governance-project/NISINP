import os

from django.utils.translation import gettext_lazy as _

PUBLIC_URL = "http://serima.monarc.lu"
ALLOWED_HOSTS = ["127.0.0.1", locals().get("PUBLIC_URL", "")]
REGULATOR_CONTACT = {
    "name": "Organization Name",
    "street": "Organization Street",
    "zip_code": "Organization Zip Code",
    "country": "Organization Country",
    "phone": "Organization Phone Number",
    "website": "https://www.example.org",
    "contact_email": "contact@example.org",
    "privacy_email": "privacy@exemple.org",
    "tos_url": None,  # "https://www.example.org/tos"
    "privacy_policy_url": None,  # "https://www.example.org/privacy_policy"
    "contact_url": None,  # "https://www.example.org/contact_us"
}

# The generic site/tool name. Used to load specific config, templates, styles, logo.
SITE_NAME = "NISINP"

SECRET_KEY = "itl44kw2RCMArqCn2XSx1Mo7d28TvKLeCon9KaSeUSI8CzeUXu"
HASH_KEY = b"Xaj5lFGAPiy2Ovzi4YmlWh-s4HHikFV4AswilOPPYN8="

DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "serima-governance",
        "USER": "<user>",
        "PASSWORD": "<password>",
        "HOST": "localhost",
        "PORT": 5432,
    },
}

CSRF_TRUSTED_ORIGINS = []
CORS_ALLOWED_ORIGINS = []
CORS_ALLOWED_ORIGIN_REGEXES = []
CORS_ALLOW_METHODS = [
    "GET",
    "OPTIONS",
]

EMAIL_HOST = "localhost"
EMAIL_PORT = 25
EMAIL_SENDER = "no-reply@monarc.lu"

API_ENABLED = False

# business configuration
MAX_PRELIMINARY_NOTIFICATION_PER_DAY_PER_USER = 3

# Logging mechanism
LOG_DIRECTORY = "./logs"
LOG_FILE = "django.log"
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "root": {"level": "INFO", "handlers": ["file"]},
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": os.path.join(LOG_DIRECTORY, LOG_FILE),
            "formatter": "app",
        },
    },
    "loggers": {
        "django": {"handlers": ["file"], "level": "INFO", "propagate": True},
    },
    "formatters": {
        "app": {
            "format": (
                "%(asctime)s [%(levelname)-8s] (%(module)s.%(funcName)s) %(message)s"
            ),
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
}

LOG_RETENTION_TIME_IN_DAY = 365
INCIDENT_RETENTION_TIME_IN_DAY = 1825
TERMS_ACCEPTANCE_TIME_IN_DAYS = 365

# TIMEOUT
SESSION_COOKIE_AGE = 15 * 60  # 15 Minutes
CSRF_COOKIE_AGE = 15 * 60

# INTERNATIONALIZATION
LANGUAGE_CODE = "en-us"

TIME_ZONE = "Europe/Luxembourg"

LANGUAGES = [
    ("en", "English"),
    ("fr", "French"),
    ("nl", _("Dutch")),
    ("de", "German"),
]

PARLER_DEFAULT_LANGUAGE_CODE = "en"
PARLER_LANGUAGES = {
    1: (
        {
            "code": "en",
        },  # English
        {
            "code": "fr",
        },  # French
        {
            "code": "nl",
        },  # Dutch
        {
            "code": "de",
        },  # German
    ),
}

# COOKIEBANNER
COOKIEBANNER = {
    "title": _("Cookie settings"),
    "groups": [
        {
            "id": "essential",
            "name": _("Essential"),
            "description": _(
                "This website uses cookies and other similar technologies strictly necessary \
                for its operation, without the use of personal data."
            ),
            "cookies": [
                {
                    "pattern": "cookiebanner",
                    "description": _("Meta cookie for the cookies that are set."),
                    "content": _("Accepted cookies"),
                    "max_age": _("6 months"),  # Set in cookie_banner.js
                },
                {
                    "pattern": "sessionid",
                    "description": _("This cookie is necessary for user options"),
                    "content": _("Session ID"),
                    "max_age": _("15 minutes"),  # SESSION_COOKIE_AGE
                },
                {
                    "pattern": "csrftoken",
                    "description": _(
                        "This cookie prevents Cross-Site-Request-Forgery attacks."
                    ),
                    "content": _("Token"),
                    "max_age": _("15 minutes"),  # CSRF_COOKIE_AGE
                },
                {
                    "pattern": "django_language",
                    "description": _("Meta cookie for user language settings"),
                    "content": _("Language settings"),
                    "max_age": _("Session"),
                },
                {
                    "pattern": "theme",
                    "description": _("Meta cookie for user theme settings"),
                    "content": _("Theme dark/light settings"),
                    "max_age": _("Session"),
                },
            ],
        }
    ],
}

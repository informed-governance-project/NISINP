# Django settings for docs project.
# import source code dir

SITE_ID = 303
DEBUG = True
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    "default": {
        "NAME": ":memory:",
        "ENGINE": "django.db.backends.sqlite3",
        "USER": "",
        "PASSWORD": "",
        "PORT": "",
    }
}

try:
    from governanceplatform import config  # type: ignore
except ImportError:  # pragma: no cover
    from governanceplatform import config_dev as config


try:
    # SECURITY WARNING: keep the secret key used in production secret!
    SECRET_KEY = config.SECRET_KEY
    HASH_KEY = config.HASH_KEY

    # SECURITY WARNING: don't run with debug turned on in production!
    DEBUG = config.DEBUG
    LOGGING = config.LOGGING
    LOG_DIRECTORY = config.LOG_DIRECTORY

    ALLOWED_HOSTS = config.ALLOWED_HOSTS
    PUBLIC_URL = config.PUBLIC_URL
    REGULATOR_CONTACT = config.REGULATOR_CONTACT
    SITE_NAME = config.SITE_NAME

    EMAIL_HOST = config.EMAIL_HOST
    EMAIL_PORT = config.EMAIL_PORT
    EMAIL_SENDER = config.EMAIL_SENDER
    DEFAULT_FROM_EMAIL = config.EMAIL_SENDER

    MAX_PRELIMINARY_NOTIFICATION_PER_DAY_PER_USER = (
        config.MAX_PRELIMINARY_NOTIFICATION_PER_DAY_PER_USER
    )
except AttributeError as e:
    print("Please check you configuration file for the missing configuration variable:")
    print(f"  {e}")
    exit(1)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "governanceplatform",
    "incidents",
    "api",
    "drf_spectacular",
    "drf_spectacular_sidecar",  # required for Django collectstatic discovery
    "corsheaders",
    "django_bootstrap5",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "django_otp.plugins.otp_static",
    "two_factor",
    "import_export",
    "parler",
    "bootstrap_datepicker_plus",
]

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

from celery import Celery

from governanceplatform import tools

__version__ = tools.get_version()

app = Celery("governanceplatform")
app.config_from_object("django.conf:settings", namespace="CELERY")

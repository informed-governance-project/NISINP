import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'governanceplatform.settings')

app = Celery('governanceplatform')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
app.autodiscover_tasks(['reporting'])

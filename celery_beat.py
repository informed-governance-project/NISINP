import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'governanceplatform.settings')

app = Celery('governanceplatform')
app.config_from_object('django.conf:settings', namespace='CELERY')

app.conf.beat_schedule = {
    "email_reminder": {
        'task': 'email_reminder',
        'schedule': crontab(minute=0) # every hour
    },
    "incident_cleaning": {
        'task': 'incident_cleaning',
        'schedule': crontab(hour=20, minute=30)
    },
    "log_cleaning": {
        'task': 'log_cleaning',
        'schedule': crontab(hour=21, minute=00)
    },
    "workflow_update_status": {
        'task': 'workflow_update_status',
        'schedule': crontab(minute=0) # every hour
    },
    "unactive_account_cleaning": {
        'task': 'unactive_account_cleaning',
        'schedule': crontab(minute=0) # every hour
    },
#    "every_10_seconds": {
#        'task': 'taskname',
#        'schedule': 10.0 # every 10 seconds
#    },
}

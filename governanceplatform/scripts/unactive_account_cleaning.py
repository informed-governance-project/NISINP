import logging
from datetime import timedelta

from django.db.models.functions import Now

from governanceplatform.models import ScriptLogEntry
from governanceplatform.settings import ACCOUNT_ACTIVATION_LINK_TIMEOUT
from governanceplatform.models import User

from celery import shared_task

logger = logging.getLogger(__name__)


# Script to run every hour
# remove users who are inactive, never logged, and recently joined
@shared_task(name="unactive_account_cleaning")
def run(logger=logger):
    logger.info("running incident_cleaning.py")
    # for all closed incident
    user_to_delete_qs = User.objects.filter(
        last_login__isnull=True,
        is_active=False,
        date_joined__lte=Now()
        - timedelta(seconds=ACCOUNT_ACTIVATION_LINK_TIMEOUT)
    )
    ScriptLogEntry.objects.create(
        object_id=None,
        object_repr="System:Inactive user script deletion "
        + str(user_to_delete_qs.count())
        + " user(s) deleted",
        action_flag=3,
    )
    user_to_delete_qs.delete()

import logging
from datetime import timedelta

from celery import shared_task
from django.db import DatabaseError
from django.db.models.functions import Now

from governanceplatform.models import ScriptLogEntry, User
from governanceplatform.settings import ACCOUNT_ACTIVATION_LINK_TIMEOUT

logger = logging.getLogger(__name__)


# Script to run every hour
# remove users who are inactive, never logged, and recently joined
@shared_task(name="unactive_account_cleaning")
def run(logger=logger):
    logger.info("running incident_cleaning.py")
    # for all closed incident
    try:
        user_to_delete_qs = User.objects.filter(
            last_login__isnull=True,
            is_active=False,
            date_joined__lte=Now() - timedelta(seconds=ACCOUNT_ACTIVATION_LINK_TIMEOUT),
        )
    except DatabaseError as e:
        logger.error("Failed to fetch users to delete: %s", e, exc_info=True)
        raise

    try:
        ScriptLogEntry.objects.create(
            object_id=None,
            object_repr="System:Inactive user script deletion "
            + str(user_to_delete_qs.count())
            + " user(s) deleted",
            action_flag=3,
        )
    except Exception as e:
        logger.error("Failed to write application log: %s", e, exc_info=True)
        raise
    logger.info("Deleting %s user(s)", user_to_delete_qs.count())
    user_to_delete_qs.delete()

import logging

from governanceplatform.permissions import update_all_group_permissions

from celery import shared_task

logger = logging.getLogger(__name__)


# Script to run once when group permissions change
@shared_task(name="update_all_group_permissions")
def run(logger=logger):
    logger.info("updating group pemissions")
    update_all_group_permissions()

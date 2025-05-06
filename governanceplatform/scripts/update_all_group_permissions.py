import logging

from governanceplatform.permissions import update_all_group_permissions

logger = logging.getLogger(__name__)


# Script to run once when group permissions change
def run(logger=logger):
    logger.info("updating group pemissions")
    update_all_group_permissions()

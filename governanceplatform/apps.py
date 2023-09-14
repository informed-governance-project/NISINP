from django.apps import AppConfig

from governanceplatform.settings import SITE_NAME


class GovernancePlatformConfig(AppConfig):
    name = "governanceplatform"
    verbose_name = SITE_NAME

    # def ready(self):
    #     from . import signals

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class GovernancePlatformConfig(AppConfig):
    name = "governanceplatform"
    verbose_name = _("Governance")

    def ready(self):
        from . import signals  # noqa: F401

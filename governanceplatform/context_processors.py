from django.utils.translation import gettext_lazy as _

from .helpers import user_in_group, is_user_regulator
from .settings import SITE_NAME


def extra_content_for_all_templates(request):
    user = request.user
    extra_data = {"site_name": SITE_NAME, "only_admin": False}

    if user_in_group(user, "PlatformAdmin") or user_in_group(user, "RegulatorAdmin"):
        extra_data["only_admin"] = True
        extra_data["template_header"] = "admin/base_site.html"
        extra_data["site_header"] = SITE_NAME + " " + _("Administration")
        extra_data["site_title"] = SITE_NAME

    extra_data["is_regulator"] = is_user_regulator(user)

    return extra_data

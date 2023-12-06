from django.utils.translation import gettext_lazy as _

from .helpers import is_user_regulator, user_in_group
from .settings import SITE_NAME


def extra_content_for_all_templates(request):
    user = request.user
    extra_data = {
        "site_name": SITE_NAME,
        "is_staff": user.is_staff,
        "is_only_admin": False,
    }
    extra_data["is_regulator"] = is_user_regulator(user)

    if user_in_group(user, "PlatformAdmin"):
        extra_data["is_only_admin"] = True
        extra_data["template_header"] = "admin/base_site.html"
        extra_data["site_header"] = SITE_NAME + " " + _("Administration")
        extra_data["site_title"] = SITE_NAME

    return extra_data

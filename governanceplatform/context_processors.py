from django.utils.translation import gettext_lazy as _

from governanceplatform import tools

from .helpers import is_user_regulator, user_in_group
from .settings import REGULATOR_CONTACT, SITE_NAME


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


def get_version(request):
    """
    Context proprocessor used to render the version of the sowftware
    in the HTML template.
    """
    return tools.get_version()


def instance_configurations(request):
    configurations = {
        "regulator": REGULATOR_CONTACT,
    }

    return configurations

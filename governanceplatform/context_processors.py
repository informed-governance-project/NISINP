from django.utils.translation import gettext_lazy as _

from governanceplatform import __version__

from .helpers import is_observer_user, is_user_regulator, user_in_group
from .models import Functionality
from .settings import REGULATOR_CONTACT, SITE_NAME


def extra_content_for_all_templates(request):
    user = request.user
    extra_data = {
        "site_name": SITE_NAME,
        "is_staff": user.is_staff,
        "is_only_admin": False,
    }
    extra_data["is_regulator"] = is_user_regulator(user)
    extra_data["is_observer"] = is_observer_user(user)

    if user_in_group(user, "PlatformAdmin"):
        extra_data["is_only_admin"] = True
        extra_data["template_header"] = "admin/base_site.html"
        extra_data["site_header"] = SITE_NAME + " " + _("Settings")
        extra_data["site_title"] = SITE_NAME

    return extra_data


def get_version(request):
    """
    Context proprocessor used to render the version of the sowftware
    in the HTML template.
    """
    return __version__


def instance_configurations(request):
    configurations = {
        "regulator": REGULATOR_CONTACT,
    }

    return configurations


def app_module_available(request):
    app_module_available = {
        "app_module_available": list(
            Functionality.objects.filter(regulator__isnull=False).values_list(
                "type", flat=True
            )
        )
    }

    return app_module_available


def user_module_permissions(request):
    user = request.user
    user_module_permissions = {}

    if user.is_authenticated:
        user_module_permissions[
            "user_module_permissions"
        ] = user.get_module_permissions()

    return user_module_permissions

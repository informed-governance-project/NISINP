from django.utils.translation import gettext_lazy as _

from .helpers import user_in_group
from .models import Company
from .settings import SITE_NAME


def extra_content_for_all_templates(request):
    user = request.user
    extra_data = {"site_name": SITE_NAME}
    extra_data["only_admin"] = False

    if user_in_group(user, "PlatformAdmin") or user_in_group(user, "RegulatorAdmin"):
        extra_data["only_admin"] = True
        extra_data["template_header"] = "admin/base_site.html"
        extra_data["site_header"] = SITE_NAME + " " + _("Administration")
        extra_data["site_title"] = SITE_NAME

    if user.is_authenticated and user.companies.exists():
        extra_data["is_regulator"] = user.companies.first().is_regulator

    company_in_use = request.session.get("company_in_use")
    if company_in_use:
        try:
            company_selected = request.user.companies.get(id=company_in_use)
            extra_data["is_regulator"] = company_selected.is_regulator
        except Company.DoesNotExist:
            pass

    return extra_data

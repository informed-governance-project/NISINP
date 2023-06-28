from django.utils.translation import gettext_lazy as _

from .models import Company
from .settings import SITE_NAME


def extra_content_for_all_templates(request):
    extra_data = {"site_name": SITE_NAME}

    if request.user.is_superuser:
        extra_data["template_header"] = "admin/base_site.html"
        extra_data["site_header"] = SITE_NAME + " " + _("Administration")
        extra_data["site_title"] = SITE_NAME

    if request.user.is_authenticated and request.user.companies.exists():
        extra_data["is_regulator"] = request.user.companies.first().is_regulator

    company_in_use = request.session.get("company_in_use")
    if company_in_use:
        try:
            company_selected = request.user.companies.get(id=company_in_use)
            extra_data["is_regulator"] = company_selected.is_regulator
        except Company.DoesNotExist:
            pass

    return extra_data

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django_otp.decorators import otp_required

from governanceplatform.models import Company, Sector, User
from governanceplatform.settings import SITE_NAME


# Customize the admin site
class CustomAdminSite(admin.AdminSite):
    site_header = SITE_NAME + " " + _("Administration")
    site_title = SITE_NAME

    def admin_view(self, view, cacheable=False):
        decorated_view = otp_required(view)
        return super().admin_view(decorated_view, cacheable)


admin_site = CustomAdminSite()


@admin.register(Sector, site=admin_site)
class SectorAdmin(admin.ModelAdmin):
    list_display = ["name", "parent"]
    search_fields = ["name"]


@admin.register(Company, site=admin_site)
class CompanyAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "address",
        "country",
        "email",
        "phone_number",
        "is_operateur",
        "is_regulator",
    ]
    list_filter = ["is_operateur", "is_regulator"]
    search_fields = ["name"]


@admin.register(User, site=admin_site)
class UserAdmin(admin.ModelAdmin):
    list_display = ["email", "first_name", "last_name", "phone_number"]
    search_fields = ["first_name", "last_name", "email"]

    fieldsets = [
        (
            None,
            {
                "classes": ["extrapretty"],
                "fields": [("first_name", "last_name"), "email", "phone_number"],
            },
        ),
    ]

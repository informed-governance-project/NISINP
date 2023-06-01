from django.contrib import admin
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _
from django_otp import devices_for_user
from django_otp.decorators import otp_required
from import_export import fields, resources
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget, ManyToManyWidget
from parler.admin import TranslatableAdmin

from governanceplatform.models import Company, Sector, Services, User
from governanceplatform.settings import SITE_NAME


# Customize the admin site
class CustomAdminSite(admin.AdminSite):
    site_header = SITE_NAME + " " + _("Administration")
    site_title = SITE_NAME

    def admin_view(self, view, cacheable=False):
        decorated_view = otp_required(view)
        return super().admin_view(decorated_view, cacheable)


admin_site = CustomAdminSite()

admin_site.register(Group)


class SectorResource(resources.ModelResource):
    id = fields.Field(
        column_name="id",
        attribute="id",
    )

    name = fields.Field(
        column_name="name",
        attribute="name",
    )

    parent = fields.Field(
        column_name="parent",
        attribute="parent",
        widget=ForeignKeyWidget(Sector, field="name"),
    )

    class Meta:
        model = Sector


@admin.register(Sector, site=admin_site)
class SectorAdmin(ImportExportModelAdmin, TranslatableAdmin):
    list_display = ["name", "parent"]
    search_fields = ["name"]
    resource_class = SectorResource


class ServicesResource(resources.ModelResource):
    id = fields.Field(
        column_name="id",
        attribute="id",
    )

    name = fields.Field(
        column_name="name",
        attribute="name",
    )

    sector = fields.Field(
        column_name="sector",
        attribute="sector",
        widget=ForeignKeyWidget(Sector, field="name"),
    )

    class Meta:
        model = Sector


@admin.register(Services, site=admin_site)
class ServicesAdmin(ImportExportModelAdmin, TranslatableAdmin):
    list_display = ["name", "sector"]
    search_fields = ["name"]
    resource_class = ServicesResource


class CompanyResource(resources.ModelResource):
    id = fields.Field(column_name="id", attribute="id")
    identifier = fields.Field(column_name="identifier", attribute="identifier")
    name = fields.Field(column_name="name", attribute="name")
    address = fields.Field(column_name="address", attribute="address")
    country = fields.Field(column_name="country", attribute="country")
    email = fields.Field(column_name="email", attribute="email")
    phone_number = fields.Field(column_name="phone_number", attribute="phone_number")
    is_regulator = fields.Field(column_name="is_regulator", attribute="is_regulator")
    monarc_path = fields.Field(column_name="monarc_path", attribute="monarc_path")
    sectors = fields.Field(
        column_name="sectors",
        attribute="sectors",
        widget=ManyToManyWidget(Sector, field="name", separator=","),
    )

    class Meta:
        model = Company


class companySectorInline(admin.TabularInline):
    model = Company.sectors.through
    verbose_name = _("sector")
    verbose_name_plural = _("sectors")
    extra = 1


@admin.register(Company, site=admin_site)
class CompanyAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    resource_class = CompanyResource
    list_display = [
        "name",
        "address",
        "country",
        "email",
        "phone_number",
        "get_sectors",
        "is_regulator",
    ]
    list_filter = ["is_regulator", "sectors"]
    search_fields = ["name"]
    filter_horizontal = ("sectors", "sectors")
    inlines = (companySectorInline,)
    fieldsets = [
        (
            _("Contact Information"),
            {
                "classes": ["extrapretty"],
                "fields": [
                    "name",
                    ("address", "country"),
                    ("email", "phone_number"),
                ],
            },
        ),
        (
            _("Permissions"),
            {
                "classes": ["extrapretty"],
                "fields": [
                    "is_regulator",
                ],
            },
        ),
        (
            _("Configuration Information"),
            {
                "classes": ["extrapretty"],
                "fields": [
                    "identifier",
                    "monarc_path",
                ],
            },
        ),
    ]


class UserResource(resources.ModelResource):
    id = fields.Field(column_name="id", attribute="id")
    first_name = fields.Field(column_name="first_name", attribute="first_name")
    last_name = fields.Field(column_name="last_name", attribute="last_name")
    email = fields.Field(column_name="email", attribute="email")
    phone_number = fields.Field(column_name="phone_number", attribute="phone_number")
    is_administrator = fields.Field(
        column_name="is_administrator", attribute="is_administrator"
    )
    companies = fields.Field(
        column_name="companies",
        attribute="companies",
        widget=ManyToManyWidget(Sector, field="name", separator=","),
    )
    sectors = fields.Field(
        column_name="sectors",
        attribute="sectors",
        widget=ManyToManyWidget(Sector, field="name", separator=","),
    )

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "is_administrator",
            "companies",
            "sectors",
        ]


class userSectorInline(admin.TabularInline):
    model = User.sectors.through
    verbose_name = _("sector")
    verbose_name_plural = _("sectors")
    extra = 1


class userCompanyInline(admin.TabularInline):
    model = User.companies.through
    verbose_name = _("company")
    verbose_name_plural = _("companies")
    extra = 1


# reset the 2FA we delete the TOTP devices
@admin.action(description=_("Reset 2FA"))
def reset_2FA(modeladmin, request, queryset):
    for user in queryset:
        devices = devices_for_user(user)
        for device in devices:
            device.delete()


@admin.register(User, site=admin_site)
class UserAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    resource_class = UserResource
    list_display = [
        "first_name",
        "last_name",
        "email",
        "phone_number",
        "get_companies",
        "get_sectors",
        "is_administrator",
    ]
    search_fields = ["first_name", "last_name", "email"]
    list_filter = [
        "sectors",
        "is_administrator",
    ]
    list_display_links = ("email", "first_name", "last_name")
    inlines = (userCompanyInline, userSectorInline)
    filter_horizontal = ("groups",)
    fieldsets = [
        (
            _("Contact Information"),
            {
                "classes": ["extrapretty"],
                "fields": [
                    ("first_name", "last_name"),
                    ("email", "phone_number"),
                ],
            },
        ),
        (
            _("Permissions"),
            {
                "classes": ["extrapretty"],
                "fields": [
                    "is_administrator",
                    "is_staff",
                ],
            },
        ),
        (
            "Group Permissions",
            {"classes": ("collapse",), "fields": ("groups", "user_permissions")},
        ),
    ]
    actions = [reset_2FA]

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if not request.user.is_superuser:
            fieldsets = [fs for fs in fieldsets if fs[0] != _("Permissions")]
        return fieldsets

    def get_inline_instances(self, request, obj=None):
        inline_instances = super().get_inline_instances(request, obj)

        if not request.user.is_superuser:
            inline_instances = [
                inline(self.model, self.admin_site) for inline in self.inlines
            ]

        return inline_instances

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        if request.user.groups.filter(name="sectorAdmin").exists():
            return queryset.filter(
                sectors__in=request.user.sectors.filter(
                    sectoradministration__is_sector_administrator=True
                ),
                companies__in=request.user.companies.all(),
            ).distinct()
        return queryset.exclude(username=request.user.username)

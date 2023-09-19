from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.auth.models import Group
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django_otp import devices_for_user
from django_otp.decorators import otp_required
from import_export import fields, resources
from import_export.admin import ExportActionModelAdmin, ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget, ManyToManyWidget
from parler.admin import TranslatableAdmin

from incidents.models import Impact

from .helpers import user_in_group
from .mixins import TranslationUpdateMixin
from .models import (
    Company,
    CompanyAdministrator,
    Functionality,
    OperatorType,
    Sector,
    SectorContact,
    Service,
    User,
)
from .settings import SITE_NAME
from .widgets import TranslatedNameM2MWidget, TranslatedNameWidget


class CustomAdminSite(admin.AdminSite):
    site_header = SITE_NAME + " " + _("Administration")
    site_title = SITE_NAME

    def admin_view(self, view, cacheable=False):
        decorated_view = otp_required(view)
        return super().admin_view(decorated_view, cacheable)


admin_site = CustomAdminSite()
admin_site.register(Site)


class SectorResource(TranslationUpdateMixin, resources.ModelResource):
    id = fields.Field(column_name="id", attribute="id", readonly=True)

    name = fields.Field(
        column_name="name",
        attribute="name",
    )

    parent = fields.Field(
        column_name="parent",
        attribute="parent",
        widget=TranslatedNameWidget(Sector, field="name"),
    )

    accronym = fields.Field(
        column_name="accronym",
        attribute="accronym",
    )

    specific_impact = fields.Field(
        column_name="specific_impact",
        attribute="specific_impact",
        widget=TranslatedNameM2MWidget(Impact, field="label", separator="\n"),
    )

    class Meta:
        model = Sector


@admin.register(Sector, site=admin_site)
class SectorAdmin(ImportExportModelAdmin, TranslatableAdmin):
    list_display = ["name", "parent", "accronym"]
    search_fields = ["name"]
    resource_class = SectorResource


class ServiceResource(TranslationUpdateMixin, resources.ModelResource):
    id = fields.Field(
        column_name="id",
        attribute="id",
    )

    name = fields.Field(
        column_name="name",
        attribute="name",
    )

    accronym = fields.Field(
        column_name="accronym",
        attribute="accronym",
    )

    sector = fields.Field(
        column_name="sector",
        attribute="sector",
        widget=TranslatedNameWidget(Sector, field="name"),
    )

    class Meta:
        model = Service


@admin.register(Service, site=admin_site)
class ServiceAdmin(ImportExportModelAdmin, TranslatableAdmin):
    list_display = ["name", "sector"]
    search_fields = ["name"]
    resource_class = ServiceResource


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
    extra = 0


class CompanySectorListFilter(SimpleListFilter):
    title = _("Sectors")
    parameter_name = "sectors"

    def lookups(self, request, model_admin):
        sectors = []
        user = request.user
        # Platform Admin
        if user_in_group(user, "PlatformAdmin"):
            pass
        # Regulator Admin
        if user_in_group(user, "RegulatorAdmin"):
            sectors = Sector.objects.all()
        # Regulator Staff
        if user_in_group(user, "RegulatorStaff"):
            sectors = Sector.objects.filter(id__in=user.sectors.all())
        # Operator Admin
        if user_in_group(user, "OperatorAdmin"):
            sectors = Sector.objects.filter(id__in=user.sectors.all())

        return [(sector.id, sector.name) for sector in sectors]

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(companies=value)
        return queryset


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
    ]
    list_filter = [CompanySectorListFilter]
    search_fields = ["name"]
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

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        user = request.user
        # Only platform Administrator can create regulator companies
        if not user_in_group(user, "PlatformAdmin"):
            fieldsets = [
                fieldset for fieldset in fieldsets if fieldset[0] != _("Permissions")
            ]

        return fieldsets

    def get_inline_instances(self, request, obj=None):
        inline_instances = super().get_inline_instances(request, obj)

        # Exclude companySectorInline for PlatformAdmin Group or if the user has a related company
        if user_in_group(request.user, "PlatformAdmin") or (
            obj and request.user.companies.filter(id=obj.id).exists()
        ):
            inline_instances = [
                inline
                for inline in inline_instances
                if not isinstance(inline, companySectorInline)
            ]

        return inline_instances

    def get_list_display(self, request):
        list_display = super().get_list_display(request)

        # Exclude "get_sectors" for PlatformAdmin Group
        if user_in_group(request.user, "PlatformAdmin"):
            list_display = [field for field in list_display if field != "get_sectors"]

        return list_display

    def get_readonly_fields(self, request, obj=None):
        # Platform Admin, Regulator Admin and Regulator Staff
        readonly_fields = super().get_readonly_fields(request, obj)
        user = request.user
        # Operator Admin
        if user_in_group(user, "OperatorAdmin"):
            readonly_fields += (
                "identifier",
                "monarc_path",
            )

        return readonly_fields

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        user = request.user
        # Platform Admin
        if user_in_group(user, "PlatformAdmin"):
            return queryset.filter(is_regulator=True)
        # Regulator Admin
        if user_in_group(user, "RegulatorAdmin"):
            return queryset.filter(
                Q(is_regulator=False) | Q(id__in=user.companies.all())
            )
        # Regulator Staff
        if user_in_group(user, "RegulatorStaff"):
            return queryset.filter(
                sectors__in=user.sectors.all(),
            ).distinct()
        # Operator Admin
        if user_in_group(user, "OperatorAdmin"):
            return queryset.filter(companyadministrator__user=user)

        return queryset


class UserResource(resources.ModelResource):
    first_name = fields.Field(column_name="first_name", attribute="first_name")
    last_name = fields.Field(column_name="last_name", attribute="last_name")
    email = fields.Field(column_name="email", attribute="email")
    phone_number = fields.Field(column_name="phone_number", attribute="phone_number")
    companies = fields.Field(
        column_name="companies",
        attribute="companies",
        widget=ManyToManyWidget(Company, field="name", separator=","),
    )
    sectors = fields.Field(
        column_name="sectors",
        attribute="sectors",
        widget=TranslatedNameM2MWidget(Sector, field="name", separator=","),
    )

    class Meta:
        model = User
        import_id_fields = ("email",)
        skip_unchanged = True
        fields = [
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "companies",
            "sectors",
        ]


class userSectorInline(admin.TabularInline):
    model = SectorContact
    verbose_name = _("sector")
    verbose_name_plural = _("sectors")
    extra = 0

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "sector":
            user = request.user
            # Platform Admin
            if user_in_group(user, "PlatformAdmin"):
                kwargs["queryset"] = Sector.objects.none()
            # Regulator Admin
            if user_in_group(user, "RegulatorAdmin"):
                kwargs["queryset"] = Sector.objects.all()
            # Regulator Staff
            if user_in_group(user, "RegulatorStaff"):
                kwargs["queryset"] = user.sectors.all()
            # Operator Admin
            if user_in_group(user, "OperatorAdmin"):
                kwargs["queryset"] = user.sectors.all()

            return super().formfield_for_foreignkey(db_field, request, **kwargs)

    # Revoke the permissions of the logged user
    def has_add_permission(self, request, obj=None):
        if obj == request.user:
            return False
        return super().has_add_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        if obj == request.user:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj == request.user:
            return False
        return super().has_delete_permission(request, obj)


class userCompanyInline(admin.TabularInline):
    model = CompanyAdministrator
    verbose_name = _("company")
    verbose_name_plural = _("companies")
    extra = 0
    min_num = 1

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "company":
            user = request.user
            # Platform Admin
            if user_in_group(user, "PlatformAdmin"):
                kwargs["queryset"] = Company.objects.filter(is_regulator=True)
            # Regulator Admin
            if user_in_group(user, "RegulatorAdmin"):
                kwargs["queryset"] = Company.objects.filter(id__in=user.companies.all())
            # Regulator Staff
            if user_in_group(user, "RegulatorStaff"):
                kwargs["queryset"] = Company.objects.filter(
                    sectors__in=user.sectors.all(),
                )
            # Operator Admin
            if user_in_group(user, "OperatorAdmin"):
                kwargs["queryset"] = user.companies.all()

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.empty_permitted = False
        return formset

    # Revoke the permissions of the logged user
    def has_add_permission(self, request, obj=None):
        if obj == request.user:
            return False
        return super().has_add_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        if obj == request.user:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj == request.user:
            return False
        return super().has_delete_permission(request, obj)


# reset the 2FA we delete the TOTP devices
@admin.action(description=_("Reset 2FA"))
def reset_2FA(modeladmin, request, queryset):
    for user in queryset:
        devices = devices_for_user(user)
        for device in devices:
            device.delete()


class UserCompaniesListFilter(SimpleListFilter):
    title = _("Companies")
    parameter_name = "companies"

    def lookups(self, request, model_admin):
        companies = []
        user = request.user
        # Platform Admin
        if user_in_group(user, "PlatformAdmin"):
            companies = Company.objects.filter(is_regulator=True)
        # Regulator Admin
        if user_in_group(user, "RegulatorAdmin"):
            companies = Company.objects.filter(id__in=user.companies.all())
        # Regulator Staff
        if user_in_group(user, "RegulatorStaff"):
            companies = Company.objects.filter(
                sectors__in=user.sectors.all(),
            )
        # Operator Admin
        if user_in_group(user, "OperatorAdmin"):
            companies = user.companies.all()

        return [(company.id, company.name) for company in companies]

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(companies=value)
        return queryset


class UserSectorListFilter(SimpleListFilter):
    title = _("Sectors")
    parameter_name = "sectors"

    def lookups(self, request, model_admin):
        sectors = []
        user = request.user
        # Platform Admin
        if user_in_group(user, "PlatformAdmin"):
            pass
        # Regulator Admin
        if user_in_group(user, "RegulatorAdmin"):
            sectors = Sector.objects.all()
        # Regulator Staff
        if user_in_group(user, "RegulatorStaff"):
            sectors = Sector.objects.filter(id__in=user.sectors.all())
        # Operator Admin
        if user_in_group(user, "OperatorAdmin"):
            sectors = Sector.objects.filter(id__in=user.sectors.all())

        return [(sector.id, sector.name) for sector in sectors]

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(companies=value)
        return queryset


@admin.register(User, site=admin_site)
class UserAdmin(ImportExportModelAdmin, ExportActionModelAdmin, admin.ModelAdmin):
    resource_class = UserResource
    list_display = [
        "first_name",
        "last_name",
        "email",
        "phone_number",
        "get_companies",
        "get_sectors",
        "is_staff",
        "proxy_token",
    ]
    search_fields = ["first_name", "last_name", "email"]
    list_filter = [
        UserCompaniesListFilter,
        UserSectorListFilter,
        "is_staff",
    ]
    list_display_links = ("email", "first_name", "last_name")
    inlines = [userCompanyInline, userSectorInline]
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
    ]
    actions = [reset_2FA]

    def get_inline_instances(self, request, obj=None):
        inline_instances = super().get_inline_instances(request, obj)

        # Exclude userCompanyInline for the logged-in user
        if obj and obj == request.user:
            inline_instances = [
                inline
                for inline in inline_instances
                if not isinstance(inline, userCompanyInline)
            ]

        # Exclude userSectorInline for users in PlatformAdmin group
        if user_in_group(request.user, "PlatformAdmin") or (
            obj and obj == request.user
        ):
            inline_instances = [
                inline
                for inline in inline_instances
                if not isinstance(inline, userSectorInline)
            ]

        return inline_instances

    def get_list_display(self, request):
        list_display = super().get_list_display(request)

        # Exclude "get_sectors" for PlatformAdmin Group
        if user_in_group(request.user, "PlatformAdmin"):
            list_display = [field for field in list_display if field != "get_sectors"]

        return list_display

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        user = request.user

        try:
            PlatformAdminGroupId = Group.objects.get(name="PlatformAdmin").id
        except ObjectDoesNotExist:
            PlatformAdminGroupId = None

        try:
            RegulatorAdminGroupId = Group.objects.get(name="RegulatorAdmin").id
        except ObjectDoesNotExist:
            RegulatorAdminGroupId = None

        try:
            RegulatorStaffGroupId = Group.objects.get(name="RegulatorStaff").id
        except ObjectDoesNotExist:
            RegulatorStaffGroupId = None

        # Platform Admin
        if user_in_group(user, "PlatformAdmin"):
            return queryset.filter(
                groups__in=[PlatformAdminGroupId, RegulatorAdminGroupId]
            )
        # Regulator Admin
        if user_in_group(user, "RegulatorAdmin"):
            return queryset.filter(
                groups__in=[RegulatorAdminGroupId, RegulatorStaffGroupId]
            )
        # Regulator Staff
        if user_in_group(user, "RegulatorStaff"):
            return queryset.filter(
                sectors__in=request.user.sectors.all(),
            ).distinct()
        # Operator Admin
        if user_in_group(user, "OperatorAdmin"):
            return queryset.filter(
                companies__in=request.user.companies.all(),
            )
        return queryset


class FunctionalityResource(TranslationUpdateMixin, resources.ModelResource):
    id = fields.Field(
        column_name="id",
        attribute="id",
    )

    name = fields.Field(
        column_name="name",
        attribute="name",
    )


@admin.register(Functionality, site=admin_site)
class FunctionalityAdmin(ImportExportModelAdmin, TranslatableAdmin):
    list_display = ["name"]
    search_fields = ["name"]
    resource_class = FunctionalityResource


class OperatorTypeResource(TranslationUpdateMixin, resources.ModelResource):
    id = fields.Field(
        column_name="id",
        attribute="id",
    )

    type = fields.Field(
        column_name="type",
        attribute="type",
    )

    functionalities = fields.Field(
        column_name="functionalities",
        attribute="functionalities",
        widget=ForeignKeyWidget(Functionality, field="name"),
    )

    class Meta:
        model = Functionality


@admin.register(OperatorType, site=admin_site)
class OperatorTypeAdmin(ImportExportModelAdmin, TranslatableAdmin):
    list_display = ["type"]
    search_fields = ["type"]
    resource_class = OperatorTypeResource

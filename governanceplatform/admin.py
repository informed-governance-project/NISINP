from django import forms
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.auth.models import Group
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django_otp import devices_for_user, user_has_device
from django_otp.decorators import otp_required
from import_export import fields, resources
from import_export.admin import ExportActionModelAdmin, ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget, ManyToManyWidget
from parler.admin import TranslatableAdmin

from .helpers import user_in_group
from .mixins import TranslationUpdateMixin
from .models import (
    Company,
    CompanyUser,
    Functionality,
    OperatorType,
    Regulation,
    Regulator,
    RegulatorUser,
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


@admin.register(Site, site=admin_site)
class SiteAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        user = request.user
        if not user_in_group(user, "PlatformAdmin"):
            return False
        return super().has_module_permission(request)


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

    acronym = fields.Field(
        column_name="acronym",
        attribute="acronym",
    )

    class Meta:
        model = Sector
        export_order = ["id", "parent"]


@admin.register(Sector, site=admin_site)
class SectorAdmin(ImportExportModelAdmin, TranslatableAdmin):
    list_display = ["acronym", "name", "parent"]
    list_display_links = ["acronym", "name"]
    search_fields = ["name"]
    resource_class = SectorResource
    fields = ("name", "parent", "acronym")
    ordering = ["id", "parent"]

    def has_change_permission(self, request, obj=None):
        user = request.user
        if user_in_group(user, "RegulatorUser"):
            return False
        return super().has_change_permission(request, obj)

    def has_module_permission(self, request):
        user = request.user
        if user_in_group(user, "RegulatorUser"):
            return False
        return super().has_module_permission(request)


class ServiceResource(TranslationUpdateMixin, resources.ModelResource):
    id = fields.Field(
        column_name="id",
        attribute="id",
    )

    name = fields.Field(
        column_name="name",
        attribute="name",
    )

    acronym = fields.Field(
        column_name="acronym",
        attribute="acronym",
    )

    sector = fields.Field(
        column_name="sector",
        attribute="sector",
        widget=TranslatedNameWidget(Sector, field="name"),
    )

    class Meta:
        model = Service
        export_order = ["sector"]


@admin.register(Service, site=admin_site)
class ServiceAdmin(ImportExportModelAdmin, TranslatableAdmin):
    list_display = ["acronym", "name", "get_sector_name", "get_subsector_name"]
    list_display_links = ["acronym", "name"]
    search_fields = ["name"]
    resource_class = ServiceResource
    fields = ("name", "acronym", "sector")
    ordering = ["sector"]

    @admin.display(description="Sector")
    def get_sector_name(self, obj):
        return obj.sector.name if not obj.sector.parent else obj.sector.parent

    @admin.display(description="Sub-sector")
    def get_subsector_name(self, obj):
        return obj.sector.name if obj.sector.parent else None


class CompanyResource(resources.ModelResource):
    id = fields.Field(column_name="id", attribute="id")
    identifier = fields.Field(column_name="identifier", attribute="identifier")
    name = fields.Field(column_name="name", attribute="name")
    address = fields.Field(column_name="address", attribute="address")
    country = fields.Field(column_name="country", attribute="country")
    email = fields.Field(column_name="email", attribute="email")
    phone_number = fields.Field(column_name="phone_number", attribute="phone_number")
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
    min_num = 1

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "sector":
            user = request.user
            # Regulator User
            if user_in_group(user, "RegulatorUser"):
                kwargs["queryset"] = user.sectors.all()
            # Operator Admin
            if user_in_group(user, "OperatorAdmin"):
                kwargs["queryset"] = user.sectors.all()

            return super().formfield_for_foreignkey(db_field, request, **kwargs)


class CompanySectorListFilter(SimpleListFilter):
    title = _("Sectors")
    parameter_name = "sectors"

    def lookups(self, request, model_admin):
        sectors = Sector.objects.all()
        user = request.user
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

    def get_list_display(self, request):
        list_display = super().get_list_display(request)

        # Exclude "get_sectors" for PlatformAdmin Group
        if user_in_group(request.user, "PlatformAdmin"):
            list_display = [field for field in list_display if field != "get_sectors"]

        return list_display

    def get_readonly_fields(self, request, obj=None):
        # Platform Admin, Regulator Admin and Regulator User
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
        # Operator Admin
        if user_in_group(user, "OperatorAdmin"):
            return queryset.filter(companyuser__user=user)

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
    regulators = fields.Field(
        column_name="regulators",
        attribute="regulators",
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
            "regulators",
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
            # Regulator User
            if user_in_group(user, "RegulatorUser"):
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


class userRegulatorInline(admin.TabularInline):
    model = RegulatorUser
    verbose_name = _("regulator")
    verbose_name_plural = _("regulators")
    extra = 0
    max_num = 1
    min_num = 1

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "regulator":
            user = request.user
            # Platform Admin
            if user_in_group(user, "PlatformAdmin"):
                kwargs["queryset"] = Regulator.objects.all()
            # Regulator Admin
            if user_in_group(user, "RegulatorAdmin"):
                kwargs["queryset"] = user.regulators.all()

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

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        if (
            user_in_group(request.user, "PlatformAdmin")
            and "is_regulator_administrator" in formset.form.base_fields
        ):
            formset.form.base_fields[
                "is_regulator_administrator"
            ].widget = forms.HiddenInput()
            formset.form.base_fields["is_regulator_administrator"].initial = True
        formset.empty_permitted = False
        return formset


class userCompanyInline(admin.TabularInline):
    model = CompanyUser
    verbose_name = _("company")
    verbose_name_plural = _("companies")
    extra = 0
    min_num = 1

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "company":
            user = request.user
            # Regulator User
            if user_in_group(user, "RegulatorUser"):
                kwargs["queryset"] = Company.objects.filter(
                    sectors__in=user.sectors.all(),
                ).distinct()
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
        companies = Company.objects.all()
        user = request.user
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
        sectors = Sector.objects.all()
        user = request.user
        # Operator Admin
        if user_in_group(user, "OperatorAdmin"):
            sectors = Sector.objects.filter(id__in=user.sectors.all())

        return [(sector.id, sector.name) for sector in sectors]

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(sectors=value)
        return queryset


class UserPermissionsGroupListFilter(SimpleListFilter):
    title = _("Roles")
    parameter_name = "roles"

    def lookups(self, request, model_admin):
        groups = Group.objects.all()
        user = request.user

        if user_in_group(user, "RegulatorAdmin"):
            groups = groups.exclude(name__in=["PlatformAdmin"])

        if user_in_group(user, "RegulatorUser"):
            groups = groups.exclude(name__in=["PlatformAdmin", "RegulatorAdmin"])

        if user_in_group(user, "OperatorAdmin"):
            groups = Group.objects.filter(id__in=user.groups.all())
        return [(group.id, group.name) for group in groups]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(groups=self.value())


@admin.register(User, site=admin_site)
class UserAdmin(ImportExportModelAdmin, ExportActionModelAdmin, admin.ModelAdmin):
    resource_class = UserResource
    list_display = [
        "first_name",
        "last_name",
        "email",
        "phone_number",
        "get_regulators",
        "get_companies",
        "get_sectors",
        "get_permissions_groups",
        "get_2FA_activation",
    ]
    search_fields = ["first_name", "last_name", "email"]
    list_filter = [
        UserCompaniesListFilter,
        UserSectorListFilter,
        UserPermissionsGroupListFilter,
    ]
    list_display_links = ("email", "first_name", "last_name")
    inlines = [userCompanyInline, userRegulatorInline, userSectorInline]
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

    @admin.display(description="2FA", boolean=True)
    def get_2FA_activation(self, obj):
        return bool(user_has_device(obj))

    def get_inline_instances(self, request, obj=None):
        inline_instances = super().get_inline_instances(request, obj)

        # Exclude userCompanyInline, userSectorInline, userRegulatorInline for the logged-in user
        if obj and obj == request.user:
            inline_instances = [
                inline
                for inline in inline_instances
                if not isinstance(
                    inline, (userCompanyInline, userSectorInline, userRegulatorInline)
                )
            ]

        # Exclude userRegulatorInline or userCompanyInline for users in RegulatorAdmin group
        if user_in_group(request.user, "RegulatorAdmin"):
            if obj and not user_in_group(obj, "RegulatorUser"):
                inline_instances = [
                    inline
                    for inline in inline_instances
                    if not isinstance(inline, userRegulatorInline)
                ]
            else:
                inline_instances = [
                    inline
                    for inline in inline_instances
                    if not isinstance(inline, userCompanyInline)
                ]

        return inline_instances

    def get_list_display(self, request):
        list_display = super().get_list_display(request)

        # Exclude "get_sectors" for PlatformAdmin Group
        if user_in_group(request.user, "PlatformAdmin"):
            list_display = [field for field in list_display if field != "get_sectors"]

        if user_in_group(request.user, "RegulatorUser"):
            list_display = [
                field for field in list_display if field != "get_regulators"
            ]

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

        # Platform Admin
        if user_in_group(user, "PlatformAdmin"):
            return queryset.filter(
                groups__in=[PlatformAdminGroupId, RegulatorAdminGroupId]
            )
        # Regulator Admin
        if user_in_group(user, "RegulatorAdmin"):
            return queryset.exclude(groups__in=[PlatformAdminGroupId]).filter(
                Q(regulators=user.regulators.first()) | Q(regulators=None)
            )
        # Regulator User
        if user_in_group(user, "RegulatorUser"):
            return queryset.exclude(
                groups__in=[PlatformAdminGroupId, RegulatorAdminGroupId]
            )
        # Operator Admin
        if user_in_group(user, "OperatorAdmin"):
            return queryset.filter(
                companies__in=request.user.companies.all(),
            )
        return queryset

    def has_change_permission(self, request, obj=None):
        user = request.user
        if user_in_group(user, "RegulatorUser") and obj == user:
            return True
        return super().has_change_permission(request, obj)


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
    fields = ("type", "functionalities")
    filter_horizontal = ["functionalities"]


class RegulatorResource(TranslationUpdateMixin, resources.ModelResource):
    id = fields.Field(
        column_name="id",
        attribute="id",
    )

    class Meta:
        model = Regulator


@admin.register(Regulator, site=admin_site)
class RegulatorAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    list_display = ["name", "full_name", "is_receiving_all_incident", "description"]
    search_fields = ["name"]
    resource_class = RegulatorResource
    fields = (
        "name",
        "full_name",
        "description",
        "country",
        "address",
        "is_receiving_all_incident",
        "monarc_path",
    )

    def has_add_permission(self, request, obj=None):
        user = request.user
        if user_in_group(user, "RegulatorAdmin"):
            return False
        return super().has_change_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        user = request.user
        if user_in_group(user, "RegulatorAdmin") and obj != user.regulators.first():
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        user = request.user
        if user_in_group(user, "RegulatorAdmin") and obj != user.regulators.first():
            return False
        return super().has_delete_permission(request, obj)


class RegulationResource(TranslationUpdateMixin, resources.ModelResource):
    id = fields.Field(
        column_name="id",
        attribute="id",
    )

    class Meta:
        model = Regulation


@admin.register(Regulation, site=admin_site)
class RegulationAdmin(ImportExportModelAdmin, TranslatableAdmin):
    list_display = ["label", "get_regulators"]
    search_fields = ["label", "regulators"]
    resource_class = RegulationResource
    fields = (
        "label",
        "regulators",
    )
    filter_horizontal = [
        "regulators",
    ]

    def has_add_permission(self, request, obj=None):
        user = request.user
        if user_in_group(user, "RegulatorAdmin"):
            return False
        return super().has_change_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        user = request.user
        if user_in_group(user, "RegulatorAdmin"):
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        user = request.user
        if user_in_group(user, "RegulatorAdmin"):
            return False
        return super().has_delete_permission(request, obj)

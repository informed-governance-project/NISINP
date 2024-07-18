from django import forms
from django.contrib import admin, messages
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
from import_export.widgets import ManyToManyWidget
from parler.admin import TranslatableAdmin

from .helpers import user_in_group, instance_user_in_group
from .mixins import TranslationUpdateMixin
from .models import (
    Cert,
    CertUser,
    Company,
    # Functionality,
    # OperatorType,
    Regulation,
    Regulator,
    RegulatorUser,
    Sector,
    SectorCompanyContact,
    # Service,
    User,
)
from .settings import SITE_NAME
from .widgets import TranslatedNameM2MWidget, TranslatedNameWidget


# get the id of a group by name
def get_group_id(name=""):
    try:
        group_id = Group.objects.get(name=name).id
    except ObjectDoesNotExist:
        group_id = None

    return group_id


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
        exclude = ('creator', 'creator_name')


@admin.register(Sector, site=admin_site)
class SectorAdmin(ImportExportModelAdmin, ExportActionModelAdmin, TranslatableAdmin):
    list_display = ["acronym", "name", "parent"]
    list_display_links = ["acronym", "name"]
    search_fields = ["translations__name"]
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

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "parent":
            # Regulator Admin
            current_id = None
            if request.resolver_match.kwargs.get("object_id"):
                current_id = request.resolver_match.kwargs["object_id"]
            kwargs["queryset"] = Sector.objects.filter(parent=None).exclude(
                pk=current_id
            )

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not change:
            try:
                obj.creator_name = request.user.regulators.all().first().name
                obj.creator_id = request.user.regulators.all().first().id
            except Exception:
                obj.creator_name = Regulator.objects.all().first().name
                obj.creator_id = Regulator.objects.all().first().id

        if obj.id and obj.parent is not None:
            if obj.id == obj.parent.id:
                messages.set_level(request, messages.WARNING)
                messages.add_message(
                    request, messages.ERROR, "A sector cannot have itself as a parent"
                )
            else:
                super().save_model(request, obj, form, change)
        else:
            super().save_model(request, obj, form, change)


# class ServiceResource(TranslationUpdateMixin, resources.ModelResource):
#     id = fields.Field(
#         column_name="id",
#         attribute="id",
#     )

#     name = fields.Field(
#         column_name="name",
#         attribute="name",
#     )

#     acronym = fields.Field(
#         column_name="acronym",
#         attribute="acronym",
#     )

#     sector = fields.Field(
#         column_name="sector",
#         attribute="sector",
#         widget=TranslatedNameWidget(Sector, field="name"),
#     )

#     class Meta:
#         model = Service
#         export_order = ["sector"]


# @admin.register(Service, site=admin_site)
# class ServiceAdmin(ImportExportModelAdmin, TranslatableAdmin):
#     list_display = ["acronym", "name", "get_sector_name", "get_subsector_name"]
#     list_display_links = ["acronym", "name"]
#     search_fields = ["translations__name"]
#     resource_class = ServiceResource
#     fields = ("name", "acronym", "sector")
#     ordering = ["sector"]

#     @admin.display(description="Sector")
#     def get_sector_name(self, obj):
#         return obj.sector.name if not obj.sector.parent else obj.sector.parent

#     @admin.display(description="Sub-sector")
#     def get_subsector_name(self, obj):
#         return obj.sector.name if obj.sector.parent else None


class CompanyResource(resources.ModelResource):
    id = fields.Field(column_name="id", attribute="id")
    identifier = fields.Field(column_name="identifier", attribute="identifier")
    name = fields.Field(column_name="name", attribute="name")
    address = fields.Field(column_name="address", attribute="address")
    country = fields.Field(column_name="country", attribute="country")
    email = fields.Field(column_name="email", attribute="email")
    phone_number = fields.Field(column_name="phone_number", attribute="phone_number")

    class Meta:
        import_id_fields = ("identifier",)
        model = Company
        exclude = ('sector_contacts', 'types')


class SectorCompanyContactInline(admin.TabularInline):
    model = SectorCompanyContact
    verbose_name = _("Contact for sector")
    verbose_name_plural = _("Contacts for sectors")
    extra = 0
    min_num = 1

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "sector":
            user = request.user
            # User
            if user_in_group(user, "RegulatorUser"):
                kwargs["queryset"] = user.get_sectors().distinct()
            # Operator Admin
            if user_in_group(user, "OperatorAdmin"):
                kwargs["queryset"] = user.sectors.all().distinct()

            return super().formfield_for_foreignkey(db_field, request, **kwargs)

        platformAdminGroupId = get_group_id("PlatformAdmin")
        certAdminGroupId = get_group_id("CertAdmin")
        certUserGroupId = get_group_id("CertUser")
        regulatorAdminGroupId = get_group_id("RegulatorAdmin")
        regulatorUserGroupId = get_group_id("RegulatorUser")
        if db_field.name == "user":
            user = request.user
            # Regulator User and admin
            if user_in_group(user, "RegulatorUser") or user_in_group(
                user, "RegulatorAdmin"
            ):
                kwargs["queryset"] = (
                    User.objects.exclude(
                        groups__in=[
                            platformAdminGroupId,
                            certAdminGroupId,
                            certUserGroupId,
                            regulatorAdminGroupId,
                            regulatorUserGroupId,
                        ]
                    )
                    .filter(regulators=None, certs=None)
                    .order_by("email")
                )

            return super().formfield_for_foreignkey(db_field, request, **kwargs)

        if db_field.name == "company":
            user = request.user
            # Regulator User
            if user_in_group(user, "RegulatorUser"):
                kwargs["queryset"] = (
                    Company.objects.all()
                    .filter(sector_contacts__in=user.get_sectors().all())
                    .order_by("name")
                )
            # Operator Admin
            if user_in_group(user, "OperatorAdmin"):
                kwargs["queryset"] = (
                    Company.objects.all()
                    .filter(
                        sectorcompanycontact__user=user,
                        sectorcompanycontact__is_company_administrator=True,
                    )
                    .order_by("name")
                )

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
        elif user_in_group(request.user, "RegulatorUser"):
            return True
        return super().has_delete_permission(request, obj)


class CompanySectorListFilter(SimpleListFilter):
    title = _("Sectors")
    parameter_name = "sector_contacts"

    def lookups(self, request, model_admin):
        sectors = Sector.objects.all()
        user = request.user
        # Operator Admin
        if user_in_group(user, "OperatorAdmin"):
            sectors = Sector.objects.filter(id__in=user.sectors.all())

        sectors_list = []
        for sector in sectors:
            if sector.name is not None and sector.parent is not None:
                sectors_list.append(
                    (sector.id, sector.parent.name + " --> " + sector.name)
                )
            elif sector.name is not None and sector.parent is None:
                sectors_list.append((sector.id, sector.name))
        return sorted(sectors_list, key=lambda item: item[1])

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(sector_contacts=value).distinct()
        return queryset


@admin.register(Company, site=admin_site)
class CompanyAdmin(ImportExportModelAdmin, ExportActionModelAdmin, admin.ModelAdmin):
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
    inlines = (SectorCompanyContactInline,)
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
                ],
            },
        ),
    ]

    def get_inline_instances(self, request, obj=None):
        inline_instances = super().get_inline_instances(request, obj)
        user = request.user
        # Exclude SectorCompanyContactInline for OperatorAdmin because if we go for user creation
        # it asks company and that's not good
        if obj and user_in_group(user, "OperatorAdmin"):
            inline_instances = [
                inline
                for inline in inline_instances
                if not isinstance(inline, SectorCompanyContactInline)
            ]

        # Exclude SectorCompanyContactInline for RegulatorAdmin because if we go for user creation
        # it asks for regulators and that's not good

        if user_in_group(user, "RegulatorAdmin"):
            inline_instances = [
                inline
                for inline in inline_instances
                if not isinstance(inline, SectorCompanyContactInline)
            ]

        # if not obj and user_in_group(user, "RegulatorUser"):
        #     inline_instances = [
        #         inline
        #         for inline in inline_instances
        #         if not isinstance(inline, SectorCompanyContactInline)
        #     ]

        return inline_instances

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
            readonly_fields += ("identifier",)

        return readonly_fields

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        user = request.user
        # Operator Admin
        if user_in_group(user, "OperatorAdmin"):
            return queryset.filter(
                sectorcompanycontact__user=user,
                sectorcompanycontact__is_company_administrator=True,
            )

        return queryset

    # we don't delete company with users
    def delete_queryset(self, request, queryset):
        all_deleted = True
        for object in queryset:
            if object.user_set.count() > 0:
                all_deleted = False
                queryset = queryset.exclude(id=object.id)

        if not all_deleted:
            messages.add_message(
                request,
                messages.WARNING,
                "Some Companies havn't been deleted because they contains users",
            )
        queryset.delete()

    def delete_model(self, request, obj):
        if obj.user_set.count() > 0:
            messages.set_level(request, messages.WARNING)
            messages.add_message(
                request,
                messages.WARNING,
                "The company has user attached and can't be deleted",
            )
        else:
            obj.delete()


class UserResource(resources.ModelResource):
    first_name = fields.Field(column_name="firstname", attribute="first_name")
    last_name = fields.Field(column_name="lastname", attribute="last_name")
    email = fields.Field(column_name="email", attribute="email")
    phone_number = fields.Field(column_name="phone_number", attribute="phone_number")
    companies = fields.Field(
        column_name="companies",
        attribute="companies",
        widget=ManyToManyWidget(Company, field="name", separator="|"),
    )
    # regulators = fields.Field(
    #     column_name="regulators",
    #     attribute="regulators",
    #     widget=ManyToManyWidget(Company, field="name", separator="|"),
    # )
    sectors = fields.Field(
        column_name="sectors",
        attribute="sectors",
        widget=TranslatedNameM2MWidget(SectorCompanyContact, separator="|"),
    )

    # override save_m2m to save the through table SectorCompanyContact
    def save_m2m(self, obj, data, using_transactions, dry_run):
        """
        Saves m2m fields.

        Model instance need to have a primary key value before
        a many-to-many relationship can be used.
        """

        if (not using_transactions and dry_run) or self._meta.use_bulk:
            # we don't have transactions and we want to do a dry_run
            # OR use_bulk is enabled (m2m operations are not supported
            # for bulk operations)
            pass
        else:
            companies = None
            sectors = None
            if 'companies' in data and 'sectors' in data:
                if data['companies']:
                    data_companies = data['companies'].split('|')
                    companies = Company.objects.filter(name__in=data_companies)
                    data_sectors = data['sectors'].split('|')
                    sectors = Sector.objects.filter(translations__name__in=data_sectors)
                    if sectors is not None and companies is not None:
                        for company in companies:
                            for sector in sectors:
                                if not SectorCompanyContact.objects.filter(user=obj, sector=sector, company=company).exists():
                                    sc = SectorCompanyContact(user=obj, sector=sector, company=company)
                                    if 'administrator' in data:
                                        if data['administrator'] is True:
                                            sc.is_company_administrator = True
                                        elif data['administrator'] is False:
                                            sc.is_company_administrator = False
                                    sc.save()

    # override skip_row to enforce role checking, we only modify Operators/incidentUser with import
    def skip_row(self, instance, original, row, import_validation_errors=None):
        if getattr(original, "pk") is not None:
            if (
                instance_user_in_group(instance, "OperatorUser")
                or instance_user_in_group(instance, "OperatorAdmin")
                or instance_user_in_group(instance, "IncidentUser")
                or instance.groups.count() == 0
            ):
                return False
            else:
                return True

        return super().skip_row(instance, original, row,
                                import_validation_errors=import_validation_errors)

    # override to put by default IncidentUser group to user without group
    def after_import_row(self, row, row_result, row_number=None, **kwargs):
        user = User.objects.get(pk=row_result.object_id)
        if user.groups.count() == 0:
            user.groups.add(Group.objects.get(name='IncidentUser').id)
            user.save()

    class Meta:
        model = User
        import_id_fields = ('email',)
        skip_unchanged = True
        fields = (
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "companies",
            "sectors",
        )


class userRegulatorInline(admin.TabularInline):
    model = RegulatorUser
    extra = 0
    min_num = 1

    filter_horizontal = [
        "sectors",
    ]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "regulator":
            user = request.user
            # Platform Admin
            if user_in_group(user, "PlatformAdmin"):
                kwargs["queryset"] = Regulator.objects.all()
            # Regulator Admin
            if user_in_group(user, "RegulatorAdmin"):
                kwargs["queryset"] = user.regulators.all()

        if db_field.name == "user":
            RegulatorAdminGroupId = get_group_id(name="RegulatorAdmin")
            RegulatorUserGroupId = get_group_id(name="RegulatorUser")
            user = request.user
            # Platform Admin
            current_id = None
            if request.resolver_match.kwargs.get("object_id"):
                current_id = request.resolver_match.kwargs["object_id"]
            if user_in_group(user, "PlatformAdmin"):
                kwargs["queryset"] = User.objects.filter(
                    Q(groups=None)
                    | Q(
                        groups__in=[RegulatorAdminGroupId, RegulatorUserGroupId],
                        regulators=None,
                    )
                    | Q(
                        groups__in=[RegulatorAdminGroupId, RegulatorUserGroupId],
                        regulators=current_id,
                    )
                )
            # Regulator Admin
            if user_in_group(user, "RegulatorAdmin"):
                kwargs["queryset"] = User.objects.filter(
                    Q(groups=None)
                    | Q(
                        groups__in=[RegulatorAdminGroupId, RegulatorUserGroupId],
                        regulators=None,
                    )
                    | Q(
                        groups__in=[RegulatorAdminGroupId, RegulatorUserGroupId],
                        regulators=user.regulators.first(),
                    )
                )

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
            # TO remove the sector choice for regulator admin
            # formset.form.base_fields[
            #     "sectors"
            # ].widget = forms.HiddenInput()
        formset.empty_permitted = False
        return formset


# reset the 2FA we delete the TOTP devices
@admin.action(description=_("Reset 2FA"))
def reset_2FA(modeladmin, request, queryset):
    for user in queryset:
        devices = devices_for_user(user)
        for device in devices:
            device.delete()


class UserRegulatorsListFilter(SimpleListFilter):
    title = _("Regulators")
    parameter_name = "regulators"

    def lookups(self, request, model_admin):
        regulators = Regulator.objects.none()
        user = request.user
        # Platform Admin
        if user_in_group(user, "PlatformAdmin"):
            regulators = Regulator.objects.all()
        return [(regulator.id, regulator.name) for regulator in regulators]

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(regulators=value)
        return queryset


class CertUsersListFilter(SimpleListFilter):
    title = _("CERT")
    parameter_name = "certs"

    def lookups(self, request, model_admin):
        certs = Cert.objects.none()
        user = request.user
        # Platform Admin
        if user_in_group(user, "PlatformAdmin"):
            certs = Cert.objects.all()
        return [(cert.id, cert.name) for cert in certs]

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(certs=value)
        return queryset


class UserCompaniesListFilter(SimpleListFilter):
    title = _("Companies")
    parameter_name = "companies"

    def lookups(self, request, model_admin):
        companies = Company.objects.all()
        user = request.user
        # Platform Admin
        if user_in_group(user, "PlatformAdmin") or user_in_group(user, "CertAdmin"):
            companies = Company.objects.none()
        # Operator Admin
        if user_in_group(user, "OperatorAdmin"):
            companies = user.companies.all()

        return [(company.id, company.name) for company in companies]

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(companies=value).distinct()
        return queryset


class UserSectorListFilter(SimpleListFilter):
    title = _("Sectors")
    parameter_name = "sectors"

    def lookups(self, request, model_admin):
        sectors = Sector.objects.all()
        user = request.user
        # Platform Admin
        if user_in_group(user, "PlatformAdmin") or user_in_group(user, "CertAdmin"):
            sectors = Sector.objects.none()
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

        if user_in_group(user, "PlatformAdmin"):
            groups = groups.exclude(
                name__in=["OperatorAdmin", "OperatorUser", "IncidentUser"]
            )

        if user_in_group(user, "CertAdmin"):
            groups = groups.exclude(
                name__in=[
                    "PlatformAdmin",
                    "RegulatorAdmin",
                    "RegulatorUser",
                    "OperatorAdmin",
                    "OperatorUser",
                    "IncidentUser",
                ]
            )

        if user_in_group(user, "RegulatorUser"):
            groups = groups.exclude(
                name__in=["PlatformAdmin", "RegulatorAdmin", "CertAdmin", "CertUser"]
            )

        if user_in_group(user, "OperatorAdmin"):
            groups = groups.filter(name__in=["OperatorAdmin", "OperatorUser"])
        return [(group.id, group.name) for group in groups]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(groups=self.value())


@admin.register(User, site=admin_site)
class UserAdmin(ImportExportModelAdmin, ExportActionModelAdmin, admin.ModelAdmin):
    resource_class = UserResource
    list_display = [
        "is_active",
        "first_name",
        "last_name",
        "email",
        "phone_number",
        "get_regulators",
        "get_companies",
        "get_certs",
        # "get_sectors",
        "get_permissions_groups",
        "get_2FA_activation",
    ]
    search_fields = ["first_name", "last_name", "email"]
    list_filter = [
        UserRegulatorsListFilter,
        CertUsersListFilter,
        UserCompaniesListFilter,
        UserSectorListFilter,
        UserPermissionsGroupListFilter,
    ]
    list_display_links = ("email", "first_name", "last_name")
    inlines = [userRegulatorInline, SectorCompanyContactInline]
    standard_fieldsets = [
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
    # add is_active for RegulatorAdmin
    admin_fieldsets = [
        (
            _("Contact Information"),
            {
                "classes": ["extrapretty"],
                "fields": [
                    ("first_name", "last_name"),
                    ("email", "phone_number"),
                    ("is_active")
                ],
            },
        ),
    ]
    actions = [reset_2FA]

    @admin.display(description="2FA", boolean=True)
    def get_2FA_activation(self, obj):
        return bool(user_has_device(obj))

    def get_fieldsets(self, request, obj=None):
        # RegulattorAdmin
        if user_in_group(request.user, "RegulatorAdmin"):
            current_id = request.resolver_match.kwargs["object_id"]
            user = User.objects.get(pk=current_id)
            if user and (
                user_in_group(user, "RegulatorAdmin")
                or user_in_group(user, "RegulatorUser")
            ):
                return self.admin_fieldsets
        # PlatformAdmin
        if user_in_group(request.user, "PlatformAdmin"):
            current_id = request.resolver_match.kwargs["object_id"]
            user = User.objects.get(pk=current_id)
            if user and (
                user_in_group(user, "RegulatorAdmin")
                or user_in_group(user, "PlatformAdmin")
            ):
                return self.admin_fieldsets
        return self.standard_fieldsets

    def get_inline_instances(self, request, obj=None):
        inline_instances = super().get_inline_instances(request, obj)

        # Exclude SectorCompanyContactInline, userRegulatorInline for the logged-in user
        if obj and obj == request.user:
            inline_instances = [
                inline
                for inline in inline_instances
                if not isinstance(
                    inline, (SectorCompanyContactInline, userRegulatorInline)
                )
            ]

        # Exclude userRegulatorInline for PlatformAdmin group
        if obj and user_in_group(obj, "PlatformAdmin"):
            inline_instances = [
                inline
                for inline in inline_instances
                if not isinstance(inline, userRegulatorInline)
            ]

        # Exclude userRegulatorInline or SectorCompanyContactInline for users in RegulatorAdmin group
        if user_in_group(request.user, "RegulatorAdmin"):
            if obj and not user_in_group(obj, "RegulatorUser"):
                inline_instances = [
                    inline
                    for inline in inline_instances
                    if not isinstance(inline, (userRegulatorInline))
                ]
            else:
                inline_instances = [
                    inline
                    for inline in inline_instances
                    if not isinstance(inline, (SectorCompanyContactInline))
                ]

        # Exclude userRegulatorInline or SectorCompanyContactInline for users in RegulatorAdmin group
        if user_in_group(request.user, "RegulatorUser"):
            if obj and not user_in_group(obj, "RegulatorUser"):
                inline_instances = [
                    inline
                    for inline in inline_instances
                    if not isinstance(inline, (userRegulatorInline))
                ]
            else:
                inline_instances = [
                    inline
                    for inline in inline_instances
                    if not isinstance(inline, (SectorCompanyContactInline))
                ]

        # platform admin just create user and manage certuser and regulatoruser entity
        if user_in_group(request.user, "PlatformAdmin"):
            inline_instances = [
                inline
                for inline in inline_instances
                if not isinstance(inline, (userRegulatorInline))
            ]

        return inline_instances

    def get_list_display(self, request):
        list_display = super().get_list_display(request)

        # Exclude "get_sectors" for PlatformAdmin Group
        if user_in_group(request.user, "PlatformAdmin"):
            fields_to_exclude = ["get_sectors", "get_companies"]
            list_display = [
                field for field in list_display if field not in fields_to_exclude
            ]

        if user_in_group(request.user, "CertAdmin"):
            fields_to_exclude = ["get_sectors", "get_companies", "get_regulators", "is_active"]
            list_display = [
                field for field in list_display if field not in fields_to_exclude
            ]

        if user_in_group(request.user, "RegulatorUser"):
            fields_to_exclude = ["get_regulators", "get_certs", "is_active"]
            list_display = [
                field for field in list_display if field not in fields_to_exclude
            ]
        if user_in_group(request.user, "OperatorAdmin"):
            fields_to_exclude = ["get_regulators", "get_certs", "is_active"]
            list_display = [
                field for field in list_display if field not in fields_to_exclude
            ]

        return list_display

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        user = request.user

        PlatformAdminGroupId = get_group_id(name="PlatformAdmin")
        RegulatorAdminGroupId = get_group_id(name="RegulatorAdmin")
        RegulatorUserGroupId = get_group_id(name="RegulatorUser")
        CertAdminGroupId = get_group_id(name="CertAdmin")
        CertUserGroupId = get_group_id(name="CertUser")

        # Platform Admin
        if user_in_group(user, "PlatformAdmin"):
            return queryset.filter(
                groups__in=[
                    PlatformAdminGroupId,
                    RegulatorAdminGroupId,
                    RegulatorUserGroupId,
                    CertUserGroupId,
                    CertAdminGroupId,
                ]
            )
        # Regulator Admin
        if user_in_group(user, "RegulatorAdmin"):
            return queryset.exclude(groups__in=[PlatformAdminGroupId]).filter(
                Q(regulators=user.regulators.first()) | Q(regulators=None)
            )
        # Regulator User
        if user_in_group(user, "RegulatorUser"):
            return queryset.exclude(
                groups__in=[
                    PlatformAdminGroupId,
                    RegulatorAdminGroupId,
                    CertUserGroupId,
                    CertAdminGroupId,
                    None,
                ],
            ).filter(~Q(groups=None))
        # Cert Admin
        if user_in_group(user, "CertAdmin"):
            return queryset.filter(Q(certs=user.certs.first()))
        # Operator Admin
        if user_in_group(user, "OperatorAdmin"):
            return queryset.filter(
                companies__in=request.user.companies.all(),
            ).distinct()
        return queryset

    def has_change_permission(self, request, obj=None):
        user = request.user
        if user_in_group(user, "RegulatorUser") and obj == user:
            return True
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj:
            if user_in_group(obj, "RegulatorUser") or user_in_group(obj, "RegulatorAdmin") or user_in_group(obj, "PlatformAdmin"):
                return False
        return True

    def save_model(self, request, obj, form, change):
        user = request.user
        if not change:
            # in CertAdmin we can only add user for our CERT and default is CertUser
            if user_in_group(user, "CertAdmin"):
                super().save_model(request, obj, form, change)
                new_group, created = Group.objects.get_or_create(name="CertUser")
                obj.certs.add(user.certs.first())
                if new_group:
                    obj.groups.add(new_group)
                else:
                    obj.groups.add(created)

            # in RegulatorUser we can only add user for operators and default is IncidentUser
            # operators have to be created under companies
            if user_in_group(user, "RegulatorUser"):
                super().save_model(request, obj, form, change)
                new_group, created = Group.objects.get_or_create(name="IncidentUser")
                if new_group:
                    obj.groups.add(new_group)
                else:
                    obj.groups.add(created)

            # in PlatformAdmin we add by default platformadmin
            # if we are not in a popup we create a platformAdmin
            if user_in_group(user, "PlatformAdmin") and "to_field=id&_popup" not in request.get_full_path():
                super().save_model(request, obj, form, change)
                new_group, created = Group.objects.get_or_create(name="PlatformAdmin")
                if new_group:
                    obj.groups.add(new_group)
                else:
                    obj.groups.add(created)

        super().save_model(request, obj, form, change)

    # override delete to don't delete RegulatorAdmin RegulatorUser and PlatformAdmin (put them inactive)
    def delete_model(self, request, obj):
        if user_in_group(obj, "RegulatorUser"):
            obj.is_active = False
        else:
            obj.delete()

# class FunctionalityResource(TranslationUpdateMixin, resources.ModelResource):
#     id = fields.Field(
#         column_name="id",
#         attribute="id",
#     )

#     name = fields.Field(
#         column_name="name",
#         attribute="name",
#     )


# @admin.register(Functionality, site=admin_site)
# class FunctionalityAdmin(ImportExportModelAdmin, TranslatableAdmin):
#     list_display = ["name"]
#     search_fields = ["translations__name"]
#     resource_class = FunctionalityResource


# class OperatorTypeResource(TranslationUpdateMixin, resources.ModelResource):
#     id = fields.Field(
#         column_name="id",
#         attribute="id",
#     )

#     type = fields.Field(
#         column_name="type",
#         attribute="type",
#     )

#     functionalities = fields.Field(
#         column_name="functionalities",
#         attribute="functionalities",
#         widget=ForeignKeyWidget(Functionality, field="name"),
#     )

#     class Meta:
#         model = Functionality


# @admin.register(OperatorType, site=admin_site)
# class OperatorTypeAdmin(ImportExportModelAdmin, TranslatableAdmin):
#     list_display = ["type"]
#     search_fields = ["translations__type"]
#     resource_class = OperatorTypeResource
#     fields = ("type", "functionalities")
#     filter_horizontal = ["functionalities"]


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
        "email_for_notification",
        "is_receiving_all_incident",
    )

    inlines = (userRegulatorInline,)

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


class CertResource(TranslationUpdateMixin, resources.ModelResource):
    id = fields.Field(
        column_name="id",
        attribute="id",
    )

    class Meta:
        model = Cert


class CertUserInline(admin.TabularInline):
    model = CertUser
    verbose_name = _("CERT user")
    verbose_name_plural = _("CERT users")
    extra = 0
    min_num = 0

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "user":
            # current_id of the parent, here a CERT
            current_id = None
            if request.resolver_match.kwargs.get("object_id"):
                current_id = request.resolver_match.kwargs["object_id"]
            query1 = User.objects.filter(
                regulators=None,
                companies=None,
                sectors=None,
                is_staff=False,
                is_superuser=False,
                sectorcompanycontact=None,
                groups=None,
                certs=None,
            )
            query_union = query1
            if current_id is not None:
                query2 = User.objects.filter(
                    certs=current_id,
                    regulators=None,
                    companies=None,
                    sectors=None,
                )
                query_union = query1.union(query2)
            kwargs["queryset"] = User.objects.filter(id__in=query_union.values("id"))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Cert, site=admin_site)
class CertAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    list_display = ["name", "full_name", "is_receiving_all_incident", "description"]
    search_fields = ["name"]
    resource_class = CertResource
    fields = (
        "name",
        "full_name",
        "description",
        "country",
        "address",
        "email_for_notification",
        "is_receiving_all_incident",
    )

    inlines = (CertUserInline,)

    def has_add_permission(self, request, obj=None):
        user = request.user
        if user_in_group(user, "RegulatorAdmin") or user_in_group(user, "CertAdmin"):
            return False
        return super().has_change_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        user = request.user
        if user_in_group(user, "RegulatorAdmin") and obj != user.certs.first():
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        user = request.user
        if user_in_group(user, "PlatformAdmin"):
            return super().has_delete_permission(request, obj)
        else:
            return False

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        user = request.user
        # Cert Admin
        if user_in_group(user, "CertAdmin"):
            return queryset.filter(
                user=user,
            )

        return queryset

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        user = request.user
        # only the platform admin can change the is_receive_all_incident
        if not user_in_group(user, "PlatformAdmin"):
            readonly_fields += ("is_receiving_all_incident",)

        return readonly_fields


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
    search_fields = ["translations__label"]
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

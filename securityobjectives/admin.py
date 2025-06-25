from django.contrib import admin
from import_export import fields, resources
from import_export.admin import ExportActionModelAdmin, ImportExportModelAdmin

from governanceplatform.admin import CustomTranslatableAdmin, admin_site
from governanceplatform.helpers import is_user_regulator
from governanceplatform.mixins import PermissionMixin, TranslationUpdateMixin
from governanceplatform.models import Regulation
from governanceplatform.widgets import TranslatedNameWidget
from securityobjectives.models import (
    Domain,
    MaturityLevel,
    SecurityMeasure,
    SecurityObjective,
    SecurityObjectiveEmail,
    SecurityObjectivesInStandard,
    Standard,
)

from .mixins import ImportMixin


class DomainResource(TranslationUpdateMixin, resources.ModelResource):
    id = fields.Field(column_name="id", attribute="id", readonly=True)
    position = fields.Field(
        column_name="position",
        attribute="position",
    )
    label = fields.Field(
        column_name="label",
        attribute="label",
    )

    def after_import_instance(self, instance, new, row_number=None, **kwargs):
        creator = kwargs.get("creator")
        if instance and creator:
            instance.creator = creator
            instance.creator_name = creator.name

    class Meta:
        model = Domain
        fields = ("label", "position")


@admin.register(Domain, site=admin_site)
class DomainAdmin(
    PermissionMixin,
    ImportMixin,
    ImportExportModelAdmin,
    ExportActionModelAdmin,
    CustomTranslatableAdmin,
):
    resource_class = DomainResource
    should_escape_html = False
    exclude = ["creator_name", "creator"]
    list_display = [
        "position",
        "label",
        "creator",
    ]
    ordering = ["position"]
    list_filter = ["creator"]


class StandardResource(TranslationUpdateMixin, resources.ModelResource):
    id = fields.Field(column_name="id", attribute="id", readonly=True)
    label = fields.Field(
        column_name="label",
        attribute="label",
    )
    description = fields.Field(
        column_name="description",
        attribute="description",
    )
    regulation = fields.Field(
        column_name="regulation",
        attribute="regulation",
        widget=TranslatedNameWidget(Regulation, field="label"),
    )

    def after_import_instance(self, instance, new, row_number=None, **kwargs):
        creator = kwargs.get("creator")
        if instance and creator:
            instance.regulator = creator

    class Meta:
        model = Standard
        fields = ("label", "description", "regulation")
        exclude = ("regulator",)


class SecurityObjectiveInline(admin.TabularInline):
    model = SecurityObjectivesInStandard
    ordering = ["position"]
    extra = 0

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        user = request.user
        if db_field.name == "security_objective":
            # Regulator
            if is_user_regulator(user):
                kwargs["queryset"] = (
                    SecurityObjective.objects.filter(creator__in=user.regulators.all())
                    .order_by("unique_code")
                    .distinct()
                )

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Standard, site=admin_site)
class StandardAdmin(
    PermissionMixin,
    ImportMixin,
    ImportExportModelAdmin,
    ExportActionModelAdmin,
    CustomTranslatableAdmin,
):
    resource_class = StandardResource
    should_escape_html = False
    list_display = ["label", "description", "regulator"]
    exclude = ("regulator",)
    inlines = (SecurityObjectiveInline,)
    list_filter = ["regulator"]

    # exclude standards which are not belonging to the user regulator
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        user = request.user
        return queryset.filter(regulator=user.regulators.first())

    # limit regulation to the one authorized by paltformadmin
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "regulation":
            regulator = request.user.regulators.first()
            kwargs["queryset"] = Regulation.objects.filter(
                regulators=regulator
            ).distinct()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    # save by default the regulator
    def save_model(self, request, obj, form, change):
        user = request.user
        obj.regulator = user.regulators.first()
        super().save_model(request, obj, form, change)


class MaturityLevelResource(TranslationUpdateMixin, resources.ModelResource):
    id = fields.Field(column_name="id", attribute="id", readonly=True)
    label = fields.Field(
        column_name="label",
        attribute="label",
    )
    level = fields.Field(
        column_name="level",
        attribute="level",
    )

    def after_import_instance(self, instance, new, row_number=None, **kwargs):
        creator = kwargs.get("creator")
        if instance and creator:
            instance.creator = creator
            instance.creator_name = creator.name

    class Meta:
        model = MaturityLevel
        fields = ("level", "label")


@admin.register(MaturityLevel, site=admin_site)
class MaturityLevelAdmin(
    PermissionMixin,
    ImportMixin,
    ImportExportModelAdmin,
    ExportActionModelAdmin,
    CustomTranslatableAdmin,
):
    resource_class = MaturityLevelResource
    should_escape_html = False
    exclude = ["creator_name", "creator"]
    list_display = ["level", "label", "creator"]
    ordering = ["level"]
    list_filter = ["creator"]


class SecurityObjectiveResource(TranslationUpdateMixin, resources.ModelResource):
    id = fields.Field(column_name="id", attribute="id", readonly=True)
    objective = fields.Field(
        column_name="objective",
        attribute="objective",
    )
    description = fields.Field(
        column_name="description",
        attribute="description",
    )
    unique_code = fields.Field(
        column_name="unique_code",
        attribute="unique_code",
    )
    domain = fields.Field(
        column_name="domain",
        attribute="domain",
    )
    standard = fields.Field(
        column_name="standard",
        attribute="stamdard",
    )
    position = fields.Field(
        column_name="position",
        attribute="position",
    )

    def after_import_instance(self, instance, new, row_number=None, **kwargs):
        creator = kwargs.get("creator")
        if instance and creator:
            instance.creator = creator
            instance.creator_name = creator.name

    # link the correct object to the row
    def before_import_row(self, row, **kwargs):
        creator = kwargs.get("creator")
        if row["domain"]:
            domain = Domain.objects.filter(
                creator=creator, translations__label=row["domain"]
            ).first()
            row["domain"] = domain
        if row["standard"]:
            standard = Standard.objects.filter(
                translations__label=row["standard"],
                regulator=creator,
            ).first()
            row["standard"] = standard
        return super().before_import_row(row, **kwargs)

    # if there is a standard get it and save the SO
    def after_import_row(self, row, row_result, row_number=None, **kwargs):
        so = SecurityObjective.objects.get(pk=row_result.object_id)
        if row["standard"] and row["position"]:
            standard = Standard.objects.filter(
                translations__label=row["standard"]
            ).first()
            if standard is not None and row["position"] is not None:
                SecurityObjectivesInStandard.objects.create(
                    security_objective=so, standard=standard, position=row["position"]
                )

    class Meta:
        model = SecurityObjective
        fields = (
            "objective",
            "description",
            "unique_code",
            "domain",
            "standard",
            "position",
        )


@admin.register(SecurityObjective, site=admin_site)
class SecurityObjectiveAdmin(
    PermissionMixin,
    ImportMixin,
    ImportExportModelAdmin,
    ExportActionModelAdmin,
    CustomTranslatableAdmin,
):
    resource_class = SecurityObjectiveResource
    should_escape_html = False
    list_display = [
        "unique_code",
        "objective",
        "description",
        "domain",
        "creator",
    ]
    exclude = ["is_archived", "creator_name", "creator"]
    list_filter = ["creator"]

    # filter only the standards that belongs to the regulators'user
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "standards":
            kwargs["queryset"] = Standard.objects.filter(
                regulator=request.user.regulators.first()
            )
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        user = request.user
        if db_field.name == "domain":
            # Regulator
            if is_user_regulator(user):
                kwargs["queryset"] = Domain.objects.filter(
                    creator__in=user.regulators.all()
                ).distinct()

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class SecurityMeasureResource(TranslationUpdateMixin, resources.ModelResource):
    id = fields.Field(column_name="id", attribute="id", readonly=True)
    security_objective = fields.Field(
        column_name="security_objective",
        attribute="security_objective",
    )
    maturity_level = fields.Field(
        column_name="maturity_level",
        attribute="maturity_level",
    )
    position = fields.Field(
        column_name="position",
        attribute="position",
    )
    description = fields.Field(
        column_name="description",
        attribute="description",
    )
    evidence = fields.Field(
        column_name="evidence",
        attribute="evidence",
    )

    def after_import_instance(self, instance, new, row_number=None, **kwargs):
        creator = kwargs.get("creator")
        if instance and creator:
            instance.creator = creator
            instance.creator_name = creator.name

    # link the correct object to the row
    def before_import_row(self, row, **kwargs):
        creator = kwargs.get("creator")
        if row["security_objective"] and creator:
            so = SecurityObjective.objects.filter(
                unique_code=row["security_objective"], creator=creator
            ).first()
            row["security_objective"] = so
        if row["maturity_level"] and creator:
            ml = MaturityLevel.objects.filter(
                translations__label=row["maturity_level"], creator=creator
            ).first()
            row["maturity_level"] = ml
        return super().before_import_row(row, **kwargs)

    class Meta:
        model = SecurityMeasure
        fields = (
            "security_objective",
            "maturity_level",
            "position",
            "description",
            "evidence",
        )


@admin.register(SecurityMeasure, site=admin_site)
class SecurityMeasureAdmin(
    PermissionMixin,
    ImportMixin,
    ImportExportModelAdmin,
    ExportActionModelAdmin,
    CustomTranslatableAdmin,
):
    resource_class = SecurityMeasureResource
    should_escape_html = False
    list_display = ["security_objective", "position", "description", "creator"]
    exclude = ["creator_name", "creator", "is_archived"]
    ordering = ["security_objective__unique_code", "position"]
    list_filter = ["creator"]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        user = request.user
        if db_field.name == "security_objective":
            # Regulator
            if is_user_regulator(user):
                kwargs["queryset"] = (
                    SecurityObjective.objects.filter(creator__in=user.regulators.all())
                    .order_by("unique_code")
                    .distinct()
                )

        if db_field.name == "maturity_level":
            # Regulator
            if is_user_regulator(user):
                kwargs["queryset"] = MaturityLevel.objects.filter(
                    creator__in=user.regulators.all()
                )

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class SOEmailResource(TranslationUpdateMixin, resources.ModelResource):
    subject = fields.Field(
        column_name="subject",
        attribute="subject",
    )

    content = fields.Field(
        column_name="content",
        attribute="content",
    )

    name = fields.Field(
        column_name="name",
        attribute="name",
    )

    class Meta:
        model = SecurityObjectiveEmail
        fields = ("id", "name", "subject", "content")
        export_order = fields


@admin.register(SecurityObjectiveEmail, site=admin_site)
class SOEmailAdmin(
    PermissionMixin, ImportMixin, ExportActionModelAdmin, CustomTranslatableAdmin
):
    list_display = [
        "name",
        "subject",
        "content",
        "creator",
    ]
    search_fields = ["translations__subject", "translations__content"]
    fields = ("name", "subject", "content")
    resource_class = SOEmailResource
    should_escape_html = False
    list_filter = ["creator"]

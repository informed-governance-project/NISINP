from django.contrib import admin
from import_export import fields, resources
from import_export.admin import ExportActionModelAdmin, ImportExportModelAdmin

from governanceplatform.admin import CustomTranslatableAdmin, admin_site
from governanceplatform.mixins import TranslationUpdateMixin
from governanceplatform.widgets import TranslatedNameM2MWidget, TranslatedNameWidget
from securityobjectives.models import (
    Domain,
    MaturityLevel,
    SecurityMeasure,
    SecurityObjective,
    SecurityObjectivesInStandard,
    Standard,
)


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

    class Meta:
        model = Domain
        fields = ("label", "position")


@admin.register(Domain, site=admin_site)
class DomainAdmin(
    ImportExportModelAdmin, ExportActionModelAdmin, CustomTranslatableAdmin
):
    resource_class = DomainResource
    list_display = [
        "label",
        "position",
    ]


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
    )

    class Meta:
        model = Standard
        fields = ("label", "description", "regulation")


class SecurityObjectiveInline(admin.TabularInline):
    model = SecurityObjectivesInStandard


@admin.register(Standard, site=admin_site)
class StandardAdmin(
    ImportExportModelAdmin, ExportActionModelAdmin, CustomTranslatableAdmin
):
    resource_class = StandardResource
    list_display = [
        "label",
        "description",
    ]
    exclude = ("regulator",)
    inlines = (SecurityObjectiveInline,)

    # exclude standards which are not belonging to the user regulator
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        user = request.user
        return queryset.filter(regulator=user.regulators.first())

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

    class Meta:
        model = MaturityLevel
        fields = ("level", "label")


@admin.register(MaturityLevel, site=admin_site)
class MaturityLevelAdmin(
    ImportExportModelAdmin, ExportActionModelAdmin, CustomTranslatableAdmin
):
    resource_class = MaturityLevelResource
    list_display = [
        "level",
        "label",
    ]


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
    position = fields.Field(
        column_name="position",
        attribute="position",
    )
    domain = fields.Field(
        column_name="domain",
        attribute="domain",
        widget=TranslatedNameWidget(Domain, field="label"),
    )
    standards = fields.Field(
        column_name="standards",
        attribute="standards",
        widget=TranslatedNameM2MWidget(Standard, field="label", separator="|"),
    )

    class Meta:
        model = SecurityObjective
        fields = (
            "objective",
            "description",
            "unique_code",
            "position",
            "domain",
            "standards",
        )


@admin.register(SecurityObjective, site=admin_site)
class SecurityObjectiveAdmin(
    ImportExportModelAdmin, ExportActionModelAdmin, CustomTranslatableAdmin
):
    resource_class = SecurityObjectiveResource
    list_display = [
        "objective",
        "description",
        "unique_code",
        "domain",
    ]
    exclude = ["is_archived"]

    # filter only the standards that belongs to the regulators'user
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "standards":
            kwargs["queryset"] = Standard.objects.filter(
                regulator=request.user.regulators.first()
            )
        return super().formfield_for_manytomany(db_field, request, **kwargs)


class SecurityMeasureResource(TranslationUpdateMixin, resources.ModelResource):
    id = fields.Field(column_name="id", attribute="id", readonly=True)
    security_objective = fields.Field(
        column_name="security_objective",
        attribute="security_objective",
        widget=TranslatedNameWidget(SecurityObjective, field="objective"),
    )
    maturity_level = fields.Field(
        column_name="maturity_level",
        attribute="maturity_level",
        widget=TranslatedNameWidget(MaturityLevel, field="label"),
    )
    description = fields.Field(
        column_name="description",
        attribute="description",
    )
    evidence = fields.Field(
        column_name="evidence",
        attribute="evidence",
    )

    class Meta:
        model = SecurityMeasure
        fields = ("security_objective", "maturity_level", "description", "evidence")


@admin.register(SecurityMeasure, site=admin_site)
class SecurityMeasureAdmin(
    ImportExportModelAdmin, ExportActionModelAdmin, CustomTranslatableAdmin
):
    resource_class = SecurityMeasureResource
    list_display = [
        "security_objective",
        "description",
        "position",
    ]

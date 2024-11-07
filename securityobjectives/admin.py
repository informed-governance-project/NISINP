from django.contrib import admin
from import_export import fields, resources
from import_export.admin import ExportActionModelAdmin, ImportExportModelAdmin

from governanceplatform.admin import CustomTranslatableAdmin, admin_site
from governanceplatform.mixins import TranslationUpdateMixin
from governanceplatform.helpers import (
    set_creator,
)
from governanceplatform.widgets import TranslatedNameWidget, TranslatedObjectNotInTheModelWidget
from securityobjectives.models import (
    Domain,
    MaturityLevel,
    SecurityMeasure,
    SecurityObjective,
    SecurityObjectivesInStandard,
    Standard,
    SecurityObjectiveEmail
)


# check if the user has access to SO
def check_access(request):
    user = request.user
    functionalities = None
    if user.regulators.first() is not None:
        functionalities = user.regulators.first().functionalities
    if user.observers.first() is not None:
        functionalities = user.observers.first().functionalities
    if functionalities is not None:
        if "securityobjectives" in functionalities.all().values_list('type', flat=True):
            return {'change': True, 'add': True}
    return {'change': False, 'add': False}


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

    def get_model_perms(self, request):
        return check_access(request)


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
    ordering = ["position"]
    extra = 0


@admin.register(Standard, site=admin_site)
class StandardAdmin(
    CustomTranslatableAdmin
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

    def get_model_perms(self, request):
        return check_access(request)


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

    def get_model_perms(self, request):
        return check_access(request)


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
        widget=TranslatedNameWidget(Domain, field="label"),
    )
    standard = fields.Field(
        column_name="standard",
        attribute="standard",
        widget=TranslatedObjectNotInTheModelWidget(Standard, field="label"),
    )
    position = fields.Field(
        column_name="position",
        attribute="position",
    )

    # if there is a standard get it and save the SO
    def after_import_row(self, row, row_result, row_number=None, **kwargs):
        so = SecurityObjective.objects.get(pk=row_result.object_id)
        if row['standard'] and row['position']:
            standard = Standard.objects.filter(translations__label=row['standard']).first()
            if standard is not None and row['position'] is not None:
                SecurityObjectivesInStandard.objects.create(
                    security_objective=so,
                    standard=standard,
                    position=row['position']
                )

    def get_export_fields(self):
        exclude_columns = ["id", "standard", "position"]
        fields = super().get_export_fields()
        return [field for field in fields if field.column_name not in exclude_columns]

    class Meta:
        import_id_fields = ("unique_code",)
        model = SecurityObjective
        exclude = ("is_archived")
        fields = (
            "objective",
            "description",
            "unique_code",
            "domain",
            "standard",
            "position"
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

    def get_model_perms(self, request):
        return check_access(request)


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

    def get_model_perms(self, request):
        return check_access(request)


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
class SOEmailAdmin(ExportActionModelAdmin, CustomTranslatableAdmin):
    list_display = [
        "name",
        "subject",
        "content",
    ]
    search_fields = ["translations__subject", "translations__content"]
    fields = ("name", "subject", "content")
    resource_class = SOEmailResource

    def save_model(self, request, obj, form, change):
        set_creator(request, obj, change)
        super().save_model(request, obj, form, change)

    def get_model_perms(self, request):
        return check_access(request)

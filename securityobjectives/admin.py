from django.contrib import admin
from import_export import fields, resources
from import_export.admin import ExportActionModelAdmin, ImportExportModelAdmin
from import_export.formats.base_formats import CSV, XLSX, JSON, XLS

from governanceplatform.admin import CustomTranslatableAdmin, admin_site
from governanceplatform.helpers import set_creator
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


# check if the user has access to SO
def check_access(request):
    user = request.user
    functionalities = None
    if user.regulators.first() is not None:
        functionalities = user.regulators.first().functionalities
    if user.observers.first() is not None:
        functionalities = user.observers.first().functionalities
    if functionalities is not None:
        if "securityobjectives" in functionalities.all().values_list("type", flat=True):
            return {"change": True, "add": True}
    return {"change": False, "add": False}


# Define the export format, and correct the export issue in terms of encoding
class RawCSV(CSV):
    def export_data(self, dataset, **kwargs):
        return dataset.export(format="csv")


class RawXLSX(XLSX):
    def export_data(self, dataset, **kwargs):
        return dataset.export(format="xlsx")


class RawJSON(JSON):
    def export_data(self, dataset, **kwargs):
        return dataset.export(format="json")


class RawXLS(XLS):
    def export_data(self, dataset, **kwargs):
        return dataset.export(format="xls")


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
    formats = [RawCSV, RawXLSX, RawJSON, RawXLS]

    def get_model_perms(self, request):
        return check_access(request)

    def import_action(self, request, *args, **kwargs):
        # Save the request to use later in the resource
        self.request = request
        return super().import_action(request, *args, **kwargs)

    def get_import_data_kwargs(self, *args, **kwargs):
        data_kwargs = super().get_import_data_kwargs(*args, **kwargs)
        cr = self.request.user.regulators.first()
        data_kwargs.update({"creator": cr})
        return data_kwargs

    def save_model(self, request, obj, form, change):
        set_creator(request, obj, change)
        super().save_model(request, obj, form, change)

    # exclude domains which are not belonging to the user regulator
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        user = request.user
        return queryset.filter(creator=user.regulators.first())


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


@admin.register(Standard, site=admin_site)
class StandardAdmin(
    PermissionMixin,
    ImportExportModelAdmin,
    ExportActionModelAdmin,
    CustomTranslatableAdmin,
):
    resource_class = StandardResource
    should_escape_html = False
    list_display = ["label", "description", "regulator"]
    exclude = ("regulator",)
    inlines = (SecurityObjectiveInline,)
    formats = [RawCSV, RawXLSX, RawJSON, RawXLS]

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

    def import_action(self, request, *args, **kwargs):
        # Save the request to use later in the resource
        self.request = request
        return super().import_action(request, *args, **kwargs)

    def get_import_data_kwargs(self, *args, **kwargs):
        data_kwargs = super().get_import_data_kwargs(*args, **kwargs)
        cr = self.request.user.regulators.first()
        data_kwargs.update({"creator": cr})
        return data_kwargs

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
    ImportExportModelAdmin,
    ExportActionModelAdmin,
    CustomTranslatableAdmin,
):
    resource_class = MaturityLevelResource
    should_escape_html = False
    exclude = ["creator_name", "creator"]
    list_display = ["level", "label", "creator"]
    ordering = ["level"]
    formats = [RawCSV, RawXLSX, RawJSON, RawXLS]

    def get_model_perms(self, request):
        return check_access(request)

    def import_action(self, request, *args, **kwargs):
        # Save the request to use later in the resource
        self.request = request
        return super().import_action(request, *args, **kwargs)

    def get_import_data_kwargs(self, *args, **kwargs):
        data_kwargs = super().get_import_data_kwargs(*args, **kwargs)
        cr = self.request.user.regulators.first()
        data_kwargs.update({"creator": cr})
        return data_kwargs

    def save_model(self, request, obj, form, change):
        set_creator(request, obj, change)
        super().save_model(request, obj, form, change)


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
    formats = [RawCSV, RawXLSX, RawJSON, RawXLS]

    # filter only the standards that belongs to the regulators'user
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "standards":
            kwargs["queryset"] = Standard.objects.filter(
                regulator=request.user.regulators.first()
            )
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def get_model_perms(self, request):
        return check_access(request)

    def import_action(self, request, *args, **kwargs):
        # Save the request to use later in the resource
        self.request = request
        return super().import_action(request, *args, **kwargs)

    def get_import_data_kwargs(self, *args, **kwargs):
        data_kwargs = super().get_import_data_kwargs(*args, **kwargs)
        cr = self.request.user.regulators.first()
        data_kwargs.update({"creator": cr})
        return data_kwargs

    def save_model(self, request, obj, form, change):
        set_creator(request, obj, change)
        super().save_model(request, obj, form, change)


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
    ImportExportModelAdmin,
    ExportActionModelAdmin,
    CustomTranslatableAdmin,
):
    resource_class = SecurityMeasureResource
    should_escape_html = False
    list_display = ["security_objective", "position", "description", "creator"]
    exclude = ["creator_name", "creator", "is_archived"]
    ordering = ["security_objective__unique_code", "position"]
    formats = [RawCSV, RawXLSX, RawJSON, RawXLS]

    def get_model_perms(self, request):
        return check_access(request)

    def import_action(self, request, *args, **kwargs):
        # Save the request to use later in the resource
        self.request = request
        return super().import_action(request, *args, **kwargs)

    def get_import_data_kwargs(self, *args, **kwargs):
        data_kwargs = super().get_import_data_kwargs(*args, **kwargs)
        cr = self.request.user.regulators.first()
        data_kwargs.update({"creator": cr})
        return data_kwargs

    def save_model(self, request, obj, form, change):
        set_creator(request, obj, change)
        super().save_model(request, obj, form, change)


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
class SOEmailAdmin(PermissionMixin, ExportActionModelAdmin, CustomTranslatableAdmin):
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

    def save_model(self, request, obj, form, change):
        set_creator(request, obj, change)
        super().save_model(request, obj, form, change)

    def get_model_perms(self, request):
        return check_access(request)

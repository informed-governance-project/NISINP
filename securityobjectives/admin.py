from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _
from import_export import fields, resources
from import_export.admin import ExportActionModelAdmin, ImportExportModelAdmin
from parler.forms import TranslatableModelForm

from governanceplatform.admin import CustomTranslatableAdmin, admin_site
from governanceplatform.helpers import generate_display_methods, is_user_regulator
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
    ExportActionModelAdmin,
    CustomTranslatableAdmin,
):
    resource_class = DomainResource
    should_escape_html = False
    exclude = ["creator_name", "creator"]
    search_fields = [
        "translations__label",
        "creator__translations__name",
        "position",
        "standard__translations__label",
    ]
    list_display = [
        "standard_display",
        "position",
        "label_display",
        "creator",
    ]

    list_filter = ["standard", "position", "translations__label", "creator"]
    translated_fields = ["label"]
    related_fields = [("standard", "label")]


for name, method in generate_display_methods(
    ["label"], [("standard", "label")]
).items():
    setattr(DomainAdmin, name, method)


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
        if db_field.name == "security_objective" and is_user_regulator(user):
            standard_id = request.resolver_match.kwargs.get("object_id")
            # update we have the standard
            if standard_id:
                linked_to_other_standards = (
                    SecurityObjectivesInStandard.objects.exclude(
                        standard_id=standard_id
                    ).values("security_objective_id")
                )

                kwargs["queryset"] = (
                    SecurityObjective.objects.filter(creator__in=user.regulators.all())
                    .exclude(id__in=linked_to_other_standards)
                    .exclude(~Q(domain__standard__id=standard_id))
                    .order_by("unique_code")
                    .distinct()
                )
            # creation we don't have the standard
            else:
                kwargs["queryset"] = (
                    SecurityObjective.objects.filter(creator__in=user.regulators.all())
                    .exclude(
                        id__in=SecurityObjectivesInStandard.objects.values(
                            "security_objective_id"
                        )
                    )
                    .exclude(~Q(domain__standard__id=standard_id))
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
    list_display = ["label_display", "description_display", "regulator"]
    search_fields = [
        "translations__label",
        "translations__description",
        "regulator__translations__name",
    ]
    exclude = ("regulator",)
    inlines = (SecurityObjectiveInline,)
    list_filter = ["translations__label", "regulator"]
    translated_fields = ["description", "label"]

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


for name, method in generate_display_methods(["label", "description"]).items():
    setattr(StandardAdmin, name, method)


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
    search_fields = [
        "translations__label",
        "creator__translations__name",
        "level",
        "standard__translations__label",
    ]
    list_display = ["standard_display", "level", "label_display", "creator"]
    list_filter = ["standard", "level", "creator"]
    translated_fields = ["label"]
    related_fields = [("standard", "label")]


for name, method in generate_display_methods(
    ["label"], [("standard", "label")]
).items():
    setattr(MaturityLevelAdmin, name, method)


class SecurityObjectiveResource(TranslationUpdateMixin, resources.ModelResource):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._row_cache = {}

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
        lang = get_language() or "en"
        if row["standard"]:
            standard = Standard.objects.filter(
                translations__label=row["standard"],
                regulator=creator,
            ).first()
            if standard:
                self._row_cache[id(row)] = {
                    "standard": standard,
                }
            if standard:
                if row["domain"]:
                    domain = (
                        Domain.objects.filter(standard=standard)
                        .translated(lang, label=row["domain"])
                        .first()
                    )
                    if not domain and row["domain_position"]:
                        domain = Domain.objects.create(
                            standard=standard,
                            position=row["domain_position"],
                            creator=creator,
                        )
                        domain.set_current_language(lang)
                        domain.label = row["domain"]
                        domain.save()
                    row["domain"] = domain

        return super().before_import_row(row, **kwargs)

    # if there is a standard get it and save the SO
    def after_import_row(self, row, row_result, row_number=None, **kwargs):
        so = SecurityObjective.objects.get(pk=row_result.object_id)
        cached = self._row_cache.pop(id(row), {})
        standard = cached.get("standard")
        if standard and so:
            sois = SecurityObjectivesInStandard.objects.filter(
                security_objective=so,
                standard=standard,
            ).first()
            if not sois:
                sois = SecurityObjectivesInStandard.objects.create(
                    security_objective=so,
                    standard=standard,
                )
            if row["priority"] and row["priority"] is not None:
                sois.priority = row["priority"]
            if row["position"] and row["position"] is not None:
                sois.position = row["position"]
            sois.save()

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
        "standard_display",
        "unique_code",
        "objective_display",
        "description_display",
        "domain",
        "creator",
    ]
    exclude = ["is_archived", "creator_name", "creator"]
    list_filter = [
        "standard",
        "unique_code",
        "translations__objective",
        "domain",
        "creator",
    ]
    translated_fields = ["description", "objective"]
    related_fields = [("domain", "label")]
    search_fields = [
        "unique_code",
        "translations__objective",
        "translations__description",
        "domain__translations__label",
        "creator__translations__name",
    ]

    @admin.display(description=_("Standard"))
    def standard_display(self, obj):
        return obj.standard_link.standard if obj.standard_link else "-"

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


for name, method in generate_display_methods(
    ["description", "objective"], [("domain", "label")]
).items():
    setattr(SecurityObjectiveAdmin, name, method)


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
        lang = get_language() or "en"
        if row["standard"]:
            standard = Standard.objects.filter(
                translations__label=row["standard"],
                regulator=creator,
            ).first()
        if standard:
            if row["security_objective"] and creator:
                so = SecurityObjective.objects.filter(
                    unique_code=row["security_objective"],
                    standard=standard,
                    creator=creator,
                ).first()
                row["security_objective"] = so
            if (
                row["maturity_level"]
                and row["maturity_level_level"] is not None
                and creator
            ):
                ml = (
                    MaturityLevel.objects.filter(
                        standard=standard,
                        level=row["maturity_level_level"],
                    )
                    .translated(lang, label=row["maturity_level"])
                    .first()
                )
                if not ml:
                    ml = MaturityLevel.objects.create(
                        standard=standard,
                        creator=creator,
                        level=row["maturity_level_level"],
                    )
                    ml.set_current_language(lang)
                    ml.label = row["maturity_level"]
                    ml.save()
                row["maturity_level"] = ml
            if row["evidence"] is None:
                row["evidence"] = ""
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


# add a custom form for SecurityMeasure to ensure that
# all the standard are the same
class SecurityMeasureAdminForm(TranslatableModelForm):
    class Meta:
        model = SecurityMeasure
        exclude = ["creator_name", "creator", "is_archived"]

    def clean(self):
        cleaned_data = super().clean()

        so = cleaned_data.get("security_objective")
        ml = cleaned_data.get("maturity_level")
        sois = SecurityObjectivesInStandard.objects.get(security_objective=so)

        if sois and ml:
            if sois.standard_id != ml.standard_id:
                raise ValidationError(
                    _(
                        "Standard of security objective and maturity level must be the same"
                    )
                )

        return cleaned_data


@admin.register(SecurityMeasure, site=admin_site)
class SecurityMeasureAdmin(
    PermissionMixin,
    ImportMixin,
    ImportExportModelAdmin,
    ExportActionModelAdmin,
    CustomTranslatableAdmin,
):
    form = SecurityMeasureAdminForm
    resource_class = SecurityMeasureResource
    should_escape_html = False
    list_display = [
        "standard_display",
        "security_objective",
        "position",
        "description_display",
        "creator",
    ]
    search_fields = [
        "security_objective__standard_link__standard__translations__label",
        "security_objective__unique_code",
        "security_objective__translations__objective",
        "translations__description",
        "position",
    ]
    ordering = ["security_objective__unique_code", "position"]
    list_filter = [
        "security_objective__standard_link__standard",
        "security_objective",
        "creator",
    ]
    translated_fields = ["description"]

    @admin.display(description=_("Standard"))
    def standard_display(self, obj):
        return (
            obj.security_objective.standard_link.standard
            if obj.security_objective.standard_link
            else "-"
        )

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


for name, method in generate_display_methods(["description"], []).items():
    setattr(SecurityMeasureAdmin, name, method)


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
        "subject_display",
        "content_display",
        "creator",
    ]
    search_fields = [
        "translations__subject",
        "translations__content",
        "creator__translations__name",
    ]
    translated_fields = ["subject", "content"]
    fields = ("name", "subject", "content")
    resource_class = SOEmailResource
    should_escape_html = False
    list_filter = ["name", "translations__subject", "creator"]


for name, method in generate_display_methods(["subject", "content"]).items():
    setattr(SOEmailAdmin, name, method)

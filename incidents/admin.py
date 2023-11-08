from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from import_export import fields, resources
from import_export.admin import ImportExportModelAdmin
from parler.admin import TranslatableAdmin, TranslatableTabularInline

from governanceplatform.admin import admin_site
from governanceplatform.mixins import TranslationUpdateMixin
from governanceplatform.models import Sector
from governanceplatform.widgets import TranslatedNameWidget
from incidents.models import (
    Email,
    Impact,
    Incident,
    PredefinedAnswer,
    Question,
    QuestionCategory,
    Workflow,
    SectorRegulation,
)


class PredefinedAnswerResource(TranslationUpdateMixin, resources.ModelResource):
    id = fields.Field(column_name="id", attribute="id", readonly=True)
    predefined_answer = fields.Field(
        column_name="predefined_answer",
        attribute="predefined_answer",
    )

    class Meta:
        model = PredefinedAnswer


@admin.register(PredefinedAnswer, site=admin_site)
class PredefinedAnswerAdmin(ImportExportModelAdmin, TranslatableAdmin):
    list_display = [
        "question",
        "predefined_answer",
        "position",
    ]
    list_display_links = ["question", "predefined_answer"]
    search_fields = ["predefined_answer"]
    resource_class = PredefinedAnswerResource


class QuestionCategoryResource(TranslationUpdateMixin, resources.ModelResource):
    id = fields.Field(column_name="id", attribute="id", readonly=True)
    label = fields.Field(
        column_name="label",
        attribute="label",
    )
    position = fields.Field(
        column_name="position",
        attribute="position",
    )

    class Meta:
        model = QuestionCategory


@admin.register(QuestionCategory, site=admin_site)
class QuestionCategoryAdmin(ImportExportModelAdmin, TranslatableAdmin):
    list_display = ["position", "label"]
    search_fields = ["label"]
    resource_class = QuestionCategoryResource
    ordering = ["position"]


class QuestionResource(TranslationUpdateMixin, resources.ModelResource):
    id = fields.Field(column_name="id", attribute="id", readonly=True)
    label = fields.Field(
        column_name="label",
        attribute="label",
    )
    tooltip = fields.Field(
        column_name="tooltip",
        attribute="tooltip",
    )
    question_type = fields.Field(
        column_name="question_type",
        attribute="question_type",
    )
    is_mandatory = fields.Field(
        column_name="is_mandatory",
        attribute="is_mandatory",
    )
    position = fields.Field(
        column_name="position",
        attribute="position",
    )
    category = fields.Field(
        column_name="category",
        attribute="category",
        widget=TranslatedNameWidget(QuestionCategory, field="label"),
    )

    class Meta:
        model = Question


class PredefinedAnswerInline(TranslatableTabularInline):
    model = PredefinedAnswer
    verbose_name = _("predefined answer")
    verbose_name_plural = _("predefined answers")
    extra = 0


@admin.register(Question, site=admin_site)
class QuestionAdmin(ImportExportModelAdmin, TranslatableAdmin):
    list_display = ["position", "category", "label", "get_predefined_answers"]
    list_display_links = ["position", "category", "label"]
    search_fields = ["label"]
    resource_class = QuestionResource
    fields = [
        ("position", "is_mandatory"),
        "question_type",
        "category",
        "label",
        "tooltip",
    ]
    inlines = (PredefinedAnswerInline,)


class ImpactResource(TranslationUpdateMixin, resources.ModelResource):
    id = fields.Field(column_name="id", attribute="id", readonly=True)
    label = fields.Field(
        column_name="label",
        attribute="label",
    )
    is_generic_impact = fields.Field(
        column_name="is_generic_impact",
        attribute="is_generic_impact",
    )

    class Meta:
        model = Impact


class ImpactSectorListFilter(SimpleListFilter):
    title = _("Sectors")
    parameter_name = "sectors"

    def lookups(self, request, model_admin):
        return [
            (sector.id, sector.name)
            for sector in Sector.objects.all().order_by("translations__name")
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                Q(sector=self.value()) | Q(sector__parent=self.value())
            )


@admin.register(Impact, site=admin_site)
class ImpactAdmin(ImportExportModelAdmin, TranslatableAdmin):
    list_display = [
        "label",
        "is_generic_impact",
    ]
    search_fields = ["translations__label"]
    resource_class = ImpactResource
    list_filter = [ImpactSectorListFilter]
    ordering = ["-is_generic_impact"]


class IncidentResource(resources.ModelResource):
    id = fields.Field(column_name="id", attribute="id", readonly=True)

    class Meta:
        model = Incident


@admin.register(Incident, site=admin_site)
class IncidentAdmin(ImportExportModelAdmin, TranslatableAdmin):
    resource_class = IncidentResource


class EmailResource(TranslationUpdateMixin, resources.ModelResource):
    email_type = fields.Field(
        column_name="email_type",
        attribute="email_type",
    )

    subject = fields.Field(
        column_name="subject",
        attribute="subject",
    )

    content = fields.Field(
        column_name="content",
        attribute="content",
    )

    class Meta:
        model = Email


@admin.register(Email, site=admin_site)
class EmailAdmin(ImportExportModelAdmin, TranslatableAdmin):
    list_display = ["email_type", "subject", "content"]
    search_fields = ["subject", "content"]
    resource_class = EmailResource


class WorkflowResource(resources.ModelResource):
    id = fields.Field(column_name="id", attribute="id", readonly=True)

    class Meta:
        model = Workflow


class WorkflowInline(admin.TabularInline):
    model = Workflow.sectorregulation_set.through
    verbose_name = _("sector regulation")
    verbose_name_plural = _("sectors regulations")
    extra = 0


@admin.register(Workflow, site=admin_site)
class WorkflowAdmin(ImportExportModelAdmin, TranslatableAdmin):
    list_display = ["name"]
    search_fields = ["name"]
    resource_class = WorkflowResource
    inlines = (WorkflowInline,)


class SectorRegulationResource(resources.ModelResource):
    id = fields.Field(column_name="id", attribute="id", readonly=True)

    class Meta:
        model = SectorRegulation


class SectorRegulationInline(admin.TabularInline):
    model = SectorRegulation.workflows.through
    verbose_name = _("sector regulation")
    verbose_name_plural = _("sectors regulations")
    extra = 0


@admin.register(SectorRegulation, site=admin_site)
class SectorRegulationAdmin(ImportExportModelAdmin, TranslatableAdmin):
    list_display = ["name"]
    search_fields = ["name"]
    resource_class = SectorRegulationResource
    inlines = (SectorRegulationInline,)

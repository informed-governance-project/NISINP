from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.db.models import Case, Q, Value, When
from django.db.models.functions import Concat
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _
from import_export import fields, resources
from import_export.admin import ImportExportModelAdmin
from parler.admin import TranslatableAdmin, TranslatableTabularInline

from governanceplatform.admin import admin_site
from governanceplatform.helpers import user_in_group
from governanceplatform.mixins import TranslationUpdateMixin
from governanceplatform.models import Regulation, Sector
from governanceplatform.widgets import TranslatedNameWidget
from incidents.models import (
    Email,
    Impact,
    Incident,
    PredefinedAnswer,
    Question,
    QuestionCategory,
    SectorRegulation,
    SectorRegulationWorkflowEmail,
    Workflow,
)


class PredefinedAnswerResource(TranslationUpdateMixin, resources.ModelResource):
    predefined_answer = fields.Field(
        column_name="predefined_answer",
        attribute="predefined_answer",
    )
    position = fields.Field(
        column_name="position",
        attribute="position",
    )
    question = fields.Field(
        attribute="question",
        column_name="question",
        widget=TranslatedNameWidget(Question, field="label"),
    )

    class Meta:
        model = PredefinedAnswer
        fields = ('id', 'predefined_answer', 'question', 'position')
        export_order = fields


@admin.register(PredefinedAnswer, site=admin_site)
class PredefinedAnswerAdmin(ImportExportModelAdmin, TranslatableAdmin):
    list_display = [
        "question",
        "predefined_answer",
        "position",
    ]
    list_display_links = ["question", "predefined_answer"]
    search_fields = ["translations__predefined_answer"]
    resource_class = PredefinedAnswerResource
    exclude = ["creator_name", "creator"]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.creator_name = request.user.regulators.all().first().name
            obj.creator_id = request.user.regulators.all().first().id
        super().save_model(request, obj, form, change)


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
        fields = ('id', 'label', 'position')
        export_order = fields


@admin.register(QuestionCategory, site=admin_site)
class QuestionCategoryAdmin(ImportExportModelAdmin, TranslatableAdmin):
    list_display = ["position", "label"]
    search_fields = ["translations__label"]
    resource_class = QuestionCategoryResource
    ordering = ["position"]
    exclude = ["creator_name", "creator"]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.creator_name = request.user.regulators.all().first().name
            obj.creator_id = request.user.regulators.all().first().id
        super().save_model(request, obj, form, change)


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
    search_fields = ["translations__label"]
    resource_class = QuestionResource
    fields = [
        ("position", "is_mandatory"),
        "question_type",
        "category",
        "label",
        "tooltip",
    ]
    inlines = (PredefinedAnswerInline,)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.creator_name = request.user.regulators.all().first().name
            obj.creator_id = request.user.regulators.all().first().id
        super().save_model(request, obj, form, change)


class ImpactResource(TranslationUpdateMixin, resources.ModelResource):
    id = fields.Field(column_name="id", attribute="id", readonly=True)
    regulation = fields.Field(
        column_name="regulation",
        attribute="regulation",
    )
    label = fields.Field(
        column_name="label",
        attribute="label",
    )

    class Meta:
        model = Impact


class ImpactSectorListFilter(SimpleListFilter):
    title = _("Sectors")
    parameter_name = "sectors"

    def lookups(self, request, model_admin):
        language = get_language()
        parents = Sector.objects.translated(language).filter(
                parent__isnull=True
            ).values_list("id", "translations__name")
        # put the conditions here to use the value of parents variable
        whens = [
            When(
                parent__id=key, then=Concat(
                            Value(value),
                            Value(" --> "),
                            "translations__name",
                        ),
            ) for key, value in parents
        ]
        return [
            (sector.id, sector.full_name)
            for sector in (
                Sector.objects.translated(get_language())
                .annotate(
                    full_name=Case(
                        *whens,
                        default="translations__name",
                    )
                )
                .order_by("full_name")
            )
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                Q(sectors=self.value()) | Q(sectors__parent=self.value())
            )


class ImpactRegulationListFilter(SimpleListFilter):
    title = _("Regulation")
    parameter_name = "regulation"

    def lookups(self, request, model_admin):
        return [
            (regulation.id, regulation.label)
            for regulation in Regulation.objects.translated(get_language()).order_by(
                "translations__label"
            )
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(Q(regulation=self.value()))


@admin.register(Impact, site=admin_site)
class ImpactAdmin(ImportExportModelAdmin, TranslatableAdmin):
    list_display = [
        "regulation",
        "get_sector_name",
        "get_subsector_name",
        "headline",
    ]
    search_fields = ["translations__label", "regulation__translations__label"]
    fields = ("regulation", "sectors", "headline", "label")
    resource_class = ImpactResource
    list_filter = [ImpactSectorListFilter, ImpactRegulationListFilter]

    @admin.display(description="Sector")
    def get_sector_name(self, obj):
        sectors = []
        for sector in obj.sectors.all():
            if not sector.parent:
                sectors.append(sector.name)
            else:
                sectors.append(sector.parent.name)
        return sectors

    @admin.display(description="Sub-sector")
    def get_subsector_name(self, obj):
        sectors = []
        for sector in obj.sectors.all():
            if sector.parent:
                sectors.append(sector.name)
            else:
                sectors.append("")
        return sectors

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        # TO DO : display a hierarchy
        # Energy
        #   -> ELEC
        #   -> GAZ
        # See MPTT
        if db_field.name == "sectors":
            language = get_language()
            parents = Sector.objects.translated(language).filter(
                    parent__isnull=True
                ).values_list("id", "translations__name")
            # put the conditions here to use the value of parents variable
            whens = [
                When(
                    parent__id=key, then=Concat(
                                Value(value),
                                Value(" --> "),
                                "translations__name",
                            ),
                ) for key, value in parents
            ]

            queryset = (
                Sector.objects.translated(language)
                .annotate(
                    full_name=Case(
                        *whens,
                        default="translations__name",
                    )
                ).order_by("full_name").distinct()
            )
            kwargs["queryset"] = queryset

        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.creator_name = request.user.regulators.all().first().name
            obj.creator_id = request.user.regulators.all().first().id
        super().save_model(request, obj, form, change)


class IncidentResource(resources.ModelResource):
    id = fields.Field(column_name="id", attribute="id", readonly=True)

    class Meta:
        model = Incident


@admin.register(Incident, site=admin_site)
class IncidentAdmin(ImportExportModelAdmin, TranslatableAdmin):
    resource_class = IncidentResource


class EmailResource(TranslationUpdateMixin, resources.ModelResource):
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
        model = Email


@admin.register(Email, site=admin_site)
class EmailAdmin(ImportExportModelAdmin, TranslatableAdmin):
    list_display = [
        "creator_name",
        "name",
        "subject",
        "content",
    ]
    search_fields = ["translations__subject", "translations__content"]
    fields = ("name", "subject", "content")
    resource_class = EmailResource

    def save_model(self, request, obj, form, change):
        if not change:
            obj.creator_name = request.user.regulators.all().first().name
            obj.creator_id = request.user.regulators.all().first().id
        super().save_model(request, obj, form, change)


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
    search_fields = ["translations__name"]
    resource_class = WorkflowResource
    inlines = (WorkflowInline,)
    fields = ("name", "questions", "is_impact_needed", "submission_email")
    filter_horizontal = [
        "questions",
    ]
    exclude = ["creator_name", "creator"]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.creator_name = request.user.regulators.all().first().name
            obj.creator_id = request.user.regulators.all().first().id
        super().save_model(request, obj, form, change)


class SectorRegulationResource(resources.ModelResource):
    id = fields.Field(column_name="id", attribute="id", readonly=True)

    class Meta:
        model = SectorRegulation


class SectorRegulationInline(admin.TabularInline):
    model = SectorRegulation.workflows.through
    verbose_name = _("Incident Report")
    verbose_name_plural = _("Incident reports")
    extra = 0


@admin.register(SectorRegulation, site=admin_site)
class SectorRegulationAdmin(ImportExportModelAdmin, TranslatableAdmin):
    list_display = ["name", "regulation", "regulator", "is_detection_date_needed"]
    search_fields = ["translations__name"]
    resource_class = SectorRegulationResource
    inlines = (SectorRegulationInline,)

    fields = (
        "name",
        "regulation",
        "regulator",
        "is_detection_date_needed",
        "sectors",
        "opening_email",
        "closing_email",
        "report_status_changed_email",
    )
    filter_horizontal = [
        "sectors",
    ]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        user = request.user
        if db_field.name == "regulation":
            # Regulator Admin
            if user_in_group(user, "RegulatorAdmin"):
                kwargs["queryset"] = Regulation.objects.filter(
                    regulators__in=user.regulators.all()
                )

        if db_field.name == "regulator":
            # Regulator Admin
            if user_in_group(user, "RegulatorAdmin"):
                kwargs["queryset"] = user.regulators.all()

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class SectorRegulationWorkflowEmailResource(
    TranslationUpdateMixin, resources.ModelResource
):
    id = fields.Field(column_name="id", attribute="id", readonly=True)

    class Meta:
        model = SectorRegulationWorkflowEmail


@admin.register(SectorRegulationWorkflowEmail, site=admin_site)
class SectorRegulationWorkflowEmailAdmin(ImportExportModelAdmin, TranslatableAdmin):
    list_display = [
        "regulation",
        "sector_regulation_workflow",
        "headline",
        "trigger_event",
        "delay_in_hours",
    ]
    search_fields = [
        "sector_regulation_workflow__workflow__translations__name",
        "headline",
    ]
    resource_class = SectorRegulationWorkflowEmailResource
    fields = (
        "sector_regulation_workflow",
        "headline",
        "email",
        "trigger_event",
        "delay_in_hours",
    )

from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Case, Q, Value, When
from django.db.models.functions import Concat
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _
from import_export import fields, resources
from import_export.admin import ExportActionModelAdmin

from governanceplatform.admin import (
    CustomTranslatableAdmin,
    CustomTranslatableTabularInline,
    admin_site,
)
from governanceplatform.globals import ACTION_FLAG_CHOICES
from governanceplatform.helpers import user_in_group
from governanceplatform.mixins import TranslationUpdateMixin
from governanceplatform.models import Regulation, Regulator, Sector, User
from governanceplatform.widgets import TranslatedNameM2MWidget, TranslatedNameWidget
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


# get the id of a group by name
def get_group_id(name=""):
    try:
        group_id = Group.objects.get(name=name).id
    except ObjectDoesNotExist:
        group_id = None

    return group_id


# filter by user
class LogUserFilter(SimpleListFilter):
    title = _("Users")
    parameter_name = "user"

    def lookups(self, request, model_admin):
        PlatformAdminGroupId = get_group_id(name="PlatformAdmin")
        RegulatorAdminGroupId = get_group_id(name="RegulatorAdmin")
        RegulatorUserGroupId = get_group_id(name="RegulatorUser")
        users = User.objects.filter(
            groups__in=[
                PlatformAdminGroupId,
                RegulatorAdminGroupId,
                RegulatorUserGroupId,
            ]
        )
        return [(user.id, user.email) for user in users]

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(user=value)
        return queryset


# filter by action
class ActionFlagFilter(SimpleListFilter):
    title = _("Action flag")
    parameter_name = "action_flag"

    def lookups(self, request, model_admin):
        return [(af, ACTION_FLAG_CHOICES[af]) for af in ACTION_FLAG_CHOICES]

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(action_flag=value)
        return queryset


# add a view to see the logs
@admin.register(LogEntry, site=admin_site)
class LogEntryAdmin(admin.ModelAdmin):
    # to have a date-based drilldown navigation in the admin page
    date_hierarchy = "action_time"

    # to filter the resultes by users, content types and action flags
    list_filter = [LogUserFilter, ActionFlagFilter]

    # when searching the user will be able to search in both object_repr and change_message
    search_fields = ["object_repr", "change_message"]

    list_display = [
        "action_time",
        "user",
        "content_type",
        "_action_flag",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    @admin.display(description=_("action flag"))
    def _action_flag(self, obj):
        return ACTION_FLAG_CHOICES[obj.action_flag]


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
        fields = ("id", "predefined_answer", "question", "position")
        export_order = fields


@admin.register(PredefinedAnswer, site=admin_site)
class PredefinedAnswerAdmin(ExportActionModelAdmin, CustomTranslatableAdmin):
    list_display = [
        "question",
        "predefined_answer",
        "position",
    ]
    list_display_links = ["question", "predefined_answer"]
    search_fields = ["translations__predefined_answer"]
    resource_class = PredefinedAnswerResource
    exclude = ["creator_name", "creator"]

    # Hidden from register models list
    def has_module_permission(self, request):
        return False

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
        fields = ("id", "label", "position")
        export_order = fields


@admin.register(QuestionCategory, site=admin_site)
class QuestionCategoryAdmin(ExportActionModelAdmin, CustomTranslatableAdmin):
    list_display = ["position", "label"]
    search_fields = ["translations__label"]
    resource_class = QuestionCategoryResource
    ordering = ["position"]
    exclude = ["creator_name", "creator"]

    # Hidden from register models list
    def has_module_permission(self, request):
        return False

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
        fields = (
            "id",
            "label",
            "tooltip",
            "question_type",
            "is_mandatory",
            "position",
            "category",
        )
        export_order = fields


class PredefinedAnswerInline(CustomTranslatableTabularInline):
    model = PredefinedAnswer
    verbose_name = _("predefined answer")
    verbose_name_plural = _("predefined answers")
    extra = 0
    exclude = ["creator", "creator_name"]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.creator_name = request.user.regulators.all().first().name
            obj.creator_id = request.user.regulators.all().first().id
        super().save_model(request, obj, form, change)


@admin.register(Question, site=admin_site)
class QuestionAdmin(ExportActionModelAdmin, CustomTranslatableAdmin):
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
        widget=TranslatedNameWidget(Regulation, field="label"),
    )
    label = fields.Field(
        column_name="label",
        attribute="label",
    )
    headline = fields.Field(
        column_name="headline",
        attribute="headline",
    )
    sectors = fields.Field(
        column_name="sectors",
        attribute="sectors",
        widget=TranslatedNameM2MWidget(Sector, field="name", separator="|"),
    )

    class Meta:
        model = Impact
        fields = ("id", "regulation", "headline", "sectors")


class ImpactSectorListFilter(SimpleListFilter):
    title = _("Sectors")
    parameter_name = "sectors"

    def lookups(self, request, model_admin):
        sectors = Sector.objects.all()
        sectors_list = []

        for sector in sectors:
            sector_name = sector.safe_translation_getter("name", any_language=True)
            if sector_name and sector.parent:
                sector_parent_name = sector.parent.safe_translation_getter(
                    "name", any_language=True
                )
                sectors_list.append(
                    (sector.id, sector_parent_name + " --> " + sector_name)
                )
            elif sector_name and sector.parent is None:
                sectors_list.append((sector.id, sector_name))
        return sorted(sectors_list, key=lambda item: item[1])

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
class ImpactAdmin(ExportActionModelAdmin, CustomTranslatableAdmin):
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
    exclude = ["creator_name", "creator"]

    filter_horizontal = [
        "sectors",
    ]

    @admin.display(description="Sector")
    def get_sector_name(self, obj):
        sectors = []
        for sector in obj.sectors.all():
            if not sector.parent:
                sectors.append(
                    sector.safe_translation_getter("name", any_language=True)
                )
            else:
                sectors.append(
                    sector.parent.safe_translation_getter("name", any_language=True)
                )
        return sectors

    @admin.display(description="Sub-sector")
    def get_subsector_name(self, obj):
        sectors = []
        for sector in obj.sectors.all():
            if sector.parent:
                sectors.append(
                    sector.safe_translation_getter("name", any_language=True)
                )
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
            parents = (
                Sector.objects.translated(language)
                .filter(parent__isnull=True)
                .values_list("id", "translations__name")
            )
            # put the conditions here to use the value of parents variable
            whens = [
                When(
                    parent__id=key,
                    then=Concat(
                        Value(value),
                        Value(" --> "),
                        "translations__name",
                    ),
                )
                for key, value in parents
            ]

            queryset = (
                Sector.objects.translated(language)
                .annotate(
                    full_name=Case(
                        *whens,
                        default="translations__name",
                    )
                )
                .order_by("full_name")
                .distinct()
            )
            kwargs["queryset"] = queryset

        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.creator_name = request.user.regulators.all().first().name
            obj.creator_id = request.user.regulators.all().first().id
        super().save_model(request, obj, form, change)


@admin.register(Incident, site=admin_site)
class IncidentAdmin(admin.ModelAdmin):
    list_display = [
        "incident_id",
        "company",
        "incident_status",
    ]


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
        fields = ("id", "name", "subject", "content")
        export_order = fields


class EmailRegulatorListFilter(SimpleListFilter):
    title = _("Regulator")
    parameter_name = "creator_id"

    def lookups(self, request, model_admin):
        return [
            (regulator.id, regulator.name)
            for regulator in Regulator.objects.translated(get_language()).order_by(
                "translations__name"
            )
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(Q(creator_id=self.value()))


class EmailTypeListFilter(SimpleListFilter):
    title = _("Email Type")
    parameter_name = ""

    def lookups(self, request, model_admin):
        return [
            ("REMINDER", "Reminder"),
            ("OPEN", "Opening Email"),
            ("CLOSE", "Closing Email"),
            ("STATUS", "Status changed"),
        ]

    def queryset(self, request, queryset):
        emails_ids = None
        if self.value() == "REMINDER":
            emails_ids = SectorRegulationWorkflowEmail.objects.values_list(
                "email__id", flat=True
            )
        elif self.value() == "OPEN":
            emails_ids = SectorRegulation.objects.values_list(
                "opening_email__id", flat=True
            )
        elif self.value() == "CLOSE":
            emails_ids = SectorRegulation.objects.values_list(
                "closing_email__id", flat=True
            )
        elif self.value() == "STATUS":
            emails_ids = SectorRegulation.objects.values_list(
                "report_status_changed_email__id", flat=True
            )
        if emails_ids is None:
            return queryset
        else:
            return queryset.filter(pk__in=emails_ids)


@admin.register(Email, site=admin_site)
class EmailAdmin(ExportActionModelAdmin, CustomTranslatableAdmin):
    list_display = [
        "creator_name",
        "name",
        "subject",
        "content",
    ]
    search_fields = ["translations__subject", "translations__content"]
    list_filter = [EmailRegulatorListFilter, EmailTypeListFilter]
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
class WorkflowAdmin(CustomTranslatableAdmin):
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
    verbose_name = _("Incident report")
    verbose_name_plural = _("Incident reports")
    extra = 0


@admin.register(SectorRegulation, site=admin_site)
class SectorRegulationAdmin(CustomTranslatableAdmin):
    list_display = ["name", "regulation", "regulator", "is_detection_date_needed"]
    search_fields = ["translations__name"]
    resource_class = SectorRegulationResource
    inlines = (SectorRegulationInline,)
    save_as = True

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

    # prevent other regulator to save the current workflow but they can duplicate
    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        if object_id:
            obj = SectorRegulation.objects.get(pk=object_id)
            if obj.regulator != request.user.regulators.all().first():
                extra_context["show_save"] = False
                extra_context["show_save_and_continue"] = False
        return super().change_view(
            request,
            object_id,
            form_url,
            extra_context=extra_context,
        )

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
class SectorRegulationWorkflowEmailAdmin(CustomTranslatableAdmin):
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

import math

from django.contrib import admin, messages
from django.contrib.admin import SimpleListFilter
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.safestring import mark_safe
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
from governanceplatform.helpers import (
    can_change_or_delete_obj,
    set_creator,
    user_in_group,
)
from governanceplatform.mixins import (
    PermissionMixin,
    ShowReminderForTranslationsMixin,
    TranslationUpdateMixin,
)
from governanceplatform.models import Regulation, Regulator, Sector, User
from governanceplatform.settings import LOG_RETENTION_TIME_IN_DAY
from governanceplatform.widgets import TranslatedNameM2MWidget, TranslatedNameWidget
from incidents.models import (
    Answer,
    Email,
    Impact,
    Incident,
    PredefinedAnswer,
    Question,
    QuestionCategory,
    QuestionCategoryOptions,
    QuestionOptions,
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
        # if obj is not None and obj.user:
        #     if not LogEntry.objects.all().filter(user=obj.user).exists():
        #         return True
        if obj is not None and obj.action_time:
            actual_time = timezone.now()
            dt = actual_time - obj.action_time
            if (
                math.floor(dt.total_seconds() / 60 / 60 / 24)
                >= LOG_RETENTION_TIME_IN_DAY
            ):
                return True
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

    class Meta:
        model = PredefinedAnswer
        fields = ("id", "predefined_answer")
        export_order = fields


@admin.register(PredefinedAnswer, site=admin_site)
class PredefinedAnswerAdmin(
    PermissionMixin, ExportActionModelAdmin, CustomTranslatableAdmin
):
    list_display = ["predefined_answer", "creator"]
    search_fields = ["translations__predefined_answer"]
    resource_class = PredefinedAnswerResource
    exclude = ["creator_name", "creator"]

    # Hidden from register models list
    def has_module_permission(self, request):
        return False

    def save_model(self, request, obj, form, change):
        set_creator(request, obj, change)
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
class QuestionCategoryAdmin(
    PermissionMixin, ExportActionModelAdmin, CustomTranslatableAdmin
):
    list_display = ["label", "creator"]
    search_fields = ["translations__label"]
    resource_class = QuestionCategoryResource
    exclude = ["creator_name", "creator"]

    # Hidden from register models list
    def has_module_permission(self, request):
        return False


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

    class Meta:
        model = Question
        fields = (
            "id",
            "label",
            "tooltip",
            "question_type",
        )
        export_order = fields


class QuestionOptionsInline(PermissionMixin, admin.TabularInline):
    model = QuestionOptions
    verbose_name = _("Question Option")
    verbose_name_plural = _("Question Options")
    ordering = ["category_option__position", "position"]
    extra = 0

    def get_max_num(self, request, obj=None, **kwargs):
        max_num = super().get_max_num(request, obj, **kwargs)
        if obj and not can_change_or_delete_obj(request, obj):
            max_num = 0
        return max_num

    # filter the question category option on the report_id to avoid mixing report categories
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "category_option" and not request.POST:
            kwargs["queryset"] = (
                QuestionCategoryOptions.objects.filter(
                    questionoptions__report=self.parent_obj
                )
                .exclude(questionoptions__report=None)
                .distinct()
            )

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class PredefinedAnswerInline(CustomTranslatableTabularInline):
    model = PredefinedAnswer
    fields = ["predefined_answer", "position"]
    verbose_name = _("predefined answer")
    verbose_name_plural = _("predefined answers")
    ordering = ["position"]
    extra = 0


@admin.register(Question, site=admin_site)
class QuestionAdmin(
    ShowReminderForTranslationsMixin,
    PermissionMixin,
    ExportActionModelAdmin,
    CustomTranslatableAdmin,
):
    list_display = ["label", "question_type", "get_predefined_answers", "creator"]
    search_fields = ["translations__label"]
    resource_class = QuestionResource
    fields = [
        "question_type",
        "label",
        "tooltip",
    ]
    inlines = [PredefinedAnswerInline]

    def save_model(self, request, obj, form, change):
        set_creator(request, obj, change)
        super().save_model(request, obj, form, change)


@admin.register(QuestionOptions, site=admin_site)
class QuestionOptionsAdmin(admin.ModelAdmin):
    list_display = ["position", "question", "is_mandatory", "category_option"]
    list_display_links = ["position", "question"]
    ordering = ["position"]
    fields = [
        ("position", "is_mandatory"),
        "question",
        "category_option",
    ]

    # Hidden from register models list
    def has_module_permission(self, request):
        return False


@admin.register(QuestionCategoryOptions, site=admin_site)
class QuestionCategoryOptionsAdmin(admin.ModelAdmin):
    list_display = ["question_category", "position"]
    list_display_links = ["position", "question_category"]
    fields = ["question_category", "position"]

    # Hidden from register models list
    def has_module_permission(self, request):
        return False


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
        sectors = Sector.objects.annotate(child_count=Count("children")).exclude(
            parent=None, child_count__gt=0
        )
        sectors_list = []

        for sector in sectors:
            sectors_list.append((sector.id, sector))
        return sorted(sectors_list, key=lambda item: str(item[1]))

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                Q(sectors=self.value()) | Q(sectors__parent=self.value())
            ).distinct()


class ImpactRegulationListFilter(SimpleListFilter):
    title = _("Legal basis")
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
class ImpactAdmin(
    ShowReminderForTranslationsMixin, ExportActionModelAdmin, CustomTranslatableAdmin
):
    list_display = [
        "regulation",
        "get_sector_name",
        "get_subsector_name",
        "headline",
    ]
    search_fields = ["translations__label", "regulation__translations__label"]
    resource_class = ImpactResource
    list_filter = [ImpactSectorListFilter, ImpactRegulationListFilter]
    exclude = ["creator_name", "creator"]
    filter_horizontal = ("sectors",)
    fieldsets = [
        (
            _("Basic information"),
            {
                "classes": ["wide", "extrapretty"],
                "fields": ["label", "headline"],
            },
        ),
        (
            _("Oversight"),
            {
                "classes": ["extrapretty"],
                "fields": [
                    "regulation",
                ],
            },
        ),
        (
            _("Sectors"),
            {
                "fields": ["sectors"],
            },
        ),
    ]

    @admin.display(description="Sector")
    def get_sector_name(self, obj):
        sectors = []
        for sector in obj.sectors.all():
            sector_name = (
                sector.parent.get_safe_translation()
                if sector.parent
                else sector.get_safe_translation()
            )
            sectors.append(sector_name)

        return sectors

    @admin.display(description="Sub-sector")
    def get_subsector_name(self, obj):
        sectors = []
        for sector in obj.sectors.all():
            sector_name = sector.get_safe_translation() if sector.parent else ""
            sectors.append(sector_name)
        return sectors

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "sectors":
            # exclude parent with children from the list
            kwargs["queryset"] = Sector.objects.annotate(
                child_count=Count("children")
            ).exclude(parent=None, child_count__gt=0)

        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        set_creator(request, obj, change)
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
class EmailAdmin(
    ShowReminderForTranslationsMixin, ExportActionModelAdmin, CustomTranslatableAdmin
):
    list_display = [
        "name",
        "subject",
        "content",
    ]
    search_fields = ["translations__subject", "translations__content"]
    list_filter = [EmailRegulatorListFilter, EmailTypeListFilter]
    fields = ("name", "subject", "content")
    resource_class = EmailResource

    def save_model(self, request, obj, form, change):
        set_creator(request, obj, change)
        super().save_model(request, obj, form, change)


@admin.register(Workflow, site=admin_site)
class WorkflowAdmin(
    ShowReminderForTranslationsMixin, PermissionMixin, CustomTranslatableAdmin
):
    list_display = ["name", "is_impact_needed", "submission_email", "creator"]
    search_fields = ["translations__name"]
    inlines = (QuestionOptionsInline,)
    save_as = True
    exclude = ["creator_name", "creator"]
    fieldsets = [
        (
            _("Basic information"),
            {
                "classes": ["wide", "extrapretty"],
                "fields": ["name", "is_impact_needed"],
            },
        ),
        (
            _("Email Notification"),
            {
                "classes": ["extrapretty"],
                "fields": [
                    "submission_email",
                ],
            },
        ),
    ]

    # give the parent object to the inlines
    def get_inline_instances(self, request, obj=None):
        inline_instances = super().get_inline_instances(request, obj)
        for inline_instance in inline_instances:
            inline_instance.parent_obj = obj
        return inline_instances

    def get_form(self, request, obj=None, **kwargs):
        if obj and not self.has_change_permission(request, obj):
            self.save_as = False
        return super().get_form(request, obj, **kwargs)

    def has_delete_permission(self, request, obj=None):
        permission = super().has_delete_permission(request, obj)
        if obj and permission:
            permission = bool(
                can_change_or_delete_obj(request, obj)
                and not Answer.objects.filter(incident_workflow__workflow=obj).exists()
            )
            if not permission and request._can_change_or_delete_obj:
                messages.warning(
                    request,
                    mark_safe(
                        _(
                            f"<strong>Delete action is not allowed</strong><br>"
                            f"- This {obj._meta.verbose_name.lower()} is either in use.<br>"
                        )
                    ),
                )
        return permission

    def save_model(self, request, obj, form, change):
        set_creator(request, obj, change)
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

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "workflow":
            kwargs["queryset"] = Workflow.objects.translated(get_language()).order_by(
                "translations__name"
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(SectorRegulation, site=admin_site)
class SectorRegulationAdmin(ShowReminderForTranslationsMixin, CustomTranslatableAdmin):
    list_display = ["name", "regulation", "regulator", "is_detection_date_needed"]
    search_fields = ["translations__name"]
    resource_class = SectorRegulationResource
    inlines = (SectorRegulationInline,)
    save_as = True
    filter_horizontal = ("sectors",)
    fieldsets = [
        (
            _("Basic information"),
            {
                "classes": ["wide", "extrapretty"],
                "fields": [
                    "name",
                    "is_detection_date_needed",
                ],
            },
        ),
        (
            _("Oversight"),
            {
                "classes": ["extrapretty"],
                "fields": [
                    "regulation",
                    "regulator",
                ],
            },
        ),
        (
            _("Sectors"),
            {
                "fields": ["sectors"],
            },
        ),
        (
            _("Email Notification"),
            {
                "classes": ["extrapretty"],
                "fields": [
                    "opening_email",
                    "closing_email",
                    "report_status_changed_email",
                ],
            },
        ),
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

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "sectors":
            # exclude parent with children from the list
            kwargs["queryset"] = Sector.objects.annotate(
                child_count=Count("children")
            ).exclude(parent=None, child_count__gt=0)

        return super().formfield_for_manytomany(db_field, request, **kwargs)


class SectorRegulationWorkflowEmailResource(
    TranslationUpdateMixin, resources.ModelResource
):
    id = fields.Field(column_name="id", attribute="id", readonly=True)

    class Meta:
        model = SectorRegulationWorkflowEmail


@admin.register(SectorRegulationWorkflowEmail, site=admin_site)
class SectorRegulationWorkflowEmailAdmin(
    ShowReminderForTranslationsMixin, CustomTranslatableAdmin
):
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

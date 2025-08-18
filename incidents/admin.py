import logging
import math

from django.contrib import admin, messages
from django.contrib.admin import SimpleListFilter
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _
from import_export import fields, resources
from import_export.admin import ExportActionModelAdmin
from parler.models import TranslatableModel

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
from governanceplatform.mixins import PermissionMixin, TranslationUpdateMixin
from governanceplatform.models import Regulation, Regulator, Sector, User
from governanceplatform.settings import LOG_RETENTION_TIME_IN_DAY
from governanceplatform.widgets import TranslatedNameM2MWidget, TranslatedNameWidget
from incidents.forms import QuestionOptionsInlineForm
from incidents.models import (
    Answer,
    Email,
    Impact,
    PredefinedAnswer,
    Question,
    QuestionCategory,
    QuestionCategoryOptions,
    QuestionOptions,
    SectorRegulation,
    SectorRegulationWorkflowEmail,
    Workflow,
)

logger = logging.getLogger(__name__)


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
        user = request.user
        user_ids = LogEntry.objects.values_list("user", flat=True).distinct()
        users = User.objects.filter(id__in=user_ids)
        PlatformAdminGroupId = get_group_id(name="PlatformAdmin")

        # Platform Admin
        if user_in_group(user, "PlatformAdmin"):
            users = users.filter(groups__in=[PlatformAdminGroupId])

        # Regulator Admin
        if user_in_group(user, "RegulatorAdmin"):
            users = users.exclude(
                groups__in=[
                    PlatformAdminGroupId,
                ]
            )

        users = users.distinct()

        return [(user.id, user.email) for user in users]

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(user=value)
        return queryset


# filter by action
class ActionFlagFilter(SimpleListFilter):
    title = _("Activity")
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
        user = request.user
        return user_in_group(user, "PlatformAdmin") or user_in_group(
            user, "RegulatorAdmin"
        )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        user = request.user

        PlatformAdminGroupId = get_group_id(name="PlatformAdmin")

        # Platform Admin
        if user_in_group(user, "PlatformAdmin"):
            return queryset.filter(user__groups__in=[PlatformAdminGroupId])

        # Regulator Admin
        if user_in_group(user, "RegulatorAdmin"):
            return queryset.exclude(
                user__groups__in=[
                    PlatformAdminGroupId,
                ]
            )

        return queryset

    @admin.display(description=_("Activity"))
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
    reference = fields.Field(
        column_name="reference",
        attribute="reference",
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
            "reference",
            "label",
            "tooltip",
            "question_type",
        )
        export_order = fields


class QuestionOptionsInline(PermissionMixin, admin.TabularInline):
    model = QuestionOptions
    form = QuestionOptionsInlineForm
    verbose_name = _("Question")
    verbose_name_plural = _("Questionnaire")
    ordering = ["category_option__position", "position"]
    exclude = ["updated_at", "deleted_date", "historic"]
    extra = 0

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(deleted_date=None)

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
    verbose_name = _("Predefined answer")
    verbose_name_plural = _("Predefined answers")
    ordering = ["position"]
    extra = 0


@admin.action(description="Duplicate selected items")
def duplicate_objects(modeladmin, request, queryset):
    config_by_model = {
        "Question": {
            "related_objects": ["predefinedanswer_set"],
            "label_field": "label",
        },
    }

    for obj in queryset:
        many_to_many_data = {}
        reverse_fk_data = {}
        model_name = obj.__class__.__name__

        if model_name not in config_by_model:
            messages.error(request, f"Duplication not supported for {model_name} model")
            continue

        config = config_by_model[model_name]
        related_objects_to_copy = config.get("related_objects", [])
        label_field = config.get("label_field")

        try:
            with transaction.atomic():
                if isinstance(obj, TranslatableModel):
                    obj_translations = list(obj.translations.all())

                for field in obj._meta.many_to_many:
                    many_to_many_data[field.name] = list(getattr(obj, field.name).all())

                for related_object in obj._meta.related_objects:
                    accessor_name = related_object.get_accessor_name()

                    if (
                        accessor_name in related_objects_to_copy
                        and related_object.one_to_many
                        and related_object.auto_created
                    ):
                        reverse_fk_data[accessor_name] = list(
                            getattr(obj, accessor_name).all()
                        )
                original_label = getattr(obj, label_field)
                obj.pk = None

                if hasattr(obj, "creator"):
                    set_creator(request, obj, False)

                obj.save()

                if obj_translations:
                    for t in obj_translations:
                        t.pk = None
                        if hasattr(t, label_field):
                            original_label = getattr(t, label_field)
                            setattr(t, label_field, f"{original_label} (copy)")
                        t.master = obj
                        t.save()

                for field_name, items in many_to_many_data.items():
                    getattr(obj, field_name).set(items)

                for related_objs in reverse_fk_data.values():
                    for related_obj in related_objs:
                        if isinstance(related_obj, TranslatableModel):
                            related_translations = list(related_obj.translations.all())

                        related_obj.pk = None
                        field_name = related_obj._meta.get_field(
                            related_object.field.name
                        ).name
                        setattr(related_obj, field_name, obj)
                        related_obj.save()

                        if related_translations:
                            for t in related_translations:
                                t.pk = None
                                t.master = related_obj
                                t.save()

                messages.success(
                    request, f"Successfully duplicated {original_label} {model_name}"
                )
        except Exception as e:
            logger.exception(f"Error duplicating object {obj.pk}: {e}")
            messages.error(request, f"Error duplicating '{obj}': {str(e)}")


@admin.register(Question, site=admin_site)
class QuestionAdmin(
    PermissionMixin,
    ExportActionModelAdmin,
    CustomTranslatableAdmin,
):
    actions = [duplicate_objects]
    list_display = [
        "reference",
        "label",
        "question_type",
        "get_predefined_answers",
        "creator",
    ]
    list_display_links = ["reference", "label"]
    search_fields = ["translations__label"]
    resource_class = QuestionResource
    fields = [
        "question_type",
        "reference",
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
    exclude = ["updated_at", "deleted_date", "historic"]

    # Hidden from register models list
    def has_module_permission(self, request):
        return False


@admin.register(QuestionCategoryOptions, site=admin_site)
class QuestionCategoryOptionsAdmin(PermissionMixin, admin.ModelAdmin):
    list_display = ["question_category", "position"]
    list_display_links = ["position", "question_category"]
    fields = ["question_category", "position"]

    # Hidden from register models list
    def has_module_permission(self, request):
        return False


class ImpactResource(TranslationUpdateMixin, resources.ModelResource):
    id = fields.Field(column_name="id", attribute="id", readonly=True)
    regulations = fields.Field(
        column_name="regulations",
        attribute="regulations",
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
        fields = ("id", "regulations", "headline", "sectors")


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
            return queryset.filter(Q(regulations=self.value()))


@admin.register(Impact, site=admin_site)
class ImpactAdmin(ExportActionModelAdmin, CustomTranslatableAdmin):
    list_display = [
        "get_regulations",
        "get_sector_name",
        "get_subsector_name",
        "headline",
    ]
    search_fields = ["translations__label", "regulation__translations__label"]
    resource_class = ImpactResource
    list_filter = [ImpactSectorListFilter, ImpactRegulationListFilter]
    exclude = ["creator_name", "creator"]
    filter_horizontal = ("sectors", "regulations")
    fieldsets = [
        (
            _("General"),
            {
                "classes": ["wide", "extrapretty"],
                "fields": ["label", "headline"],
            },
        ),
        (
            _("Supervision"),
            {
                "classes": ["extrapretty"],
                "fields": [
                    "regulations",
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

    @admin.display(description="Regulations")
    def get_regulations(self, obj):
        return ", ".join([c.label for c in obj.regulations.all()])

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
    title = _("Email type")
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
class WorkflowAdmin(PermissionMixin, CustomTranslatableAdmin):
    list_display = [
        "name",
        "label",
        "description",
        "is_impact_needed",
        "submission_email",
        "creator",
    ]
    search_fields = ["translations__label"]
    inlines = (QuestionOptionsInline,)
    save_as = True
    exclude = ["creator_name", "creator"]
    fieldsets = [
        (
            _("General"),
            {
                "classes": ["wide", "extrapretty"],
                "fields": ["name", "label", "description", "is_impact_needed"],
            },
        ),
        (
            _("Notification Email"),
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
                message = _(
                    "<strong>Deletion forbidden</strong><br>"
                    "- This {object_name} is either in use.<br>"
                )
                object_name = obj._meta.verbose_name.lower()

                messages.warning(request, format_html(message, object_name=object_name))
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
            kwargs["queryset"] = Workflow.objects.order_by(
                "name"
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(SectorRegulation, site=admin_site)
class SectorRegulationAdmin(CustomTranslatableAdmin, PermissionMixin):
    list_display = ["name", "regulation", "regulator", "is_detection_date_needed"]
    search_fields = ["translations__name"]
    resource_class = SectorRegulationResource
    inlines = (SectorRegulationInline,)
    save_as = True
    filter_horizontal = ("sectors",)
    fieldsets = [
        (
            _("General"),
            {
                "classes": ["wide", "extrapretty"],
                "fields": [
                    "name",
                    "is_detection_date_needed",
                ],
            },
        ),
        (
            _("Supervision"),
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
            _("Notification Email"),
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

    def has_delete_permission(self, request, obj=None):
        permission = super().has_delete_permission(request, obj)
        header_message = _(
            "<strong>Deletion is not allowed.</strong><br>"
            "- This {object_name} is either in use.<br>"
            "- You are not its creator ({creator_name})"
        )
        if obj and permission:
            permission = can_change_or_delete_obj(request, obj, header_message)

            if not permission and request._can_change_or_delete_obj:
                message = _(
                    "<strong>Deletion forbidden</strong><br>"
                    "- This {object_name} is either in use.<br>"
                )
                object_name = obj._meta.verbose_name.lower()

                messages.warning(request, format_html(message, object_name=object_name))
        return permission


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
        "sector_regulation_workflow__sector_regulation__regulation__translations__label",
        "translations__headline",
    ]
    resource_class = SectorRegulationWorkflowEmailResource
    fields = (
        "sector_regulation_workflow",
        "headline",
        "email",
        "trigger_event",
        "delay_in_hours",
    )

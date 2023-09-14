from django.contrib import admin
from import_export import fields, resources
from import_export.admin import ImportExportModelAdmin
from parler.admin import TranslatableAdmin

from governanceplatform.admin import admin_site
from governanceplatform.mixins import TranslationUpdateMixin
from governanceplatform.widgets import TranslatedNameM2MWidget, TranslatedNameWidget
from incidents.models import (
    Email,
    Impact,
    Incident,
    PredifinedAnswer,
    Question,
    QuestionCategory,
    RegulationType,
)


class PredifinedAnswerResource(TranslationUpdateMixin, resources.ModelResource):
    id = fields.Field(column_name="id", attribute="id", readonly=True)
    predifined_answer = fields.Field(
        column_name="predifined_answer",
        attribute="predifined_answer",
    )
    allowed_additional_answer = fields.Field(
        column_name="allowed_additional_answer",
        attribute="allowed_additional_answer",
    )

    class Meta:
        model = PredifinedAnswer


@admin.register(PredifinedAnswer, site=admin_site)
class PredifinedAnswerAdmin(ImportExportModelAdmin, TranslatableAdmin):
    list_display = ["predifined_answer", "allowed_additional_answer"]
    search_fields = ["allowed_additional_answer, predifined_answer"]
    resource_class = PredifinedAnswerResource


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
    list_display = ["label", "position"]
    search_fields = ["label"]
    resource_class = QuestionCategoryResource


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

    is_preliminary = fields.Field(
        column_name="is_preliminary",
        attribute="is_preliminary",
    )

    predifined_answers = fields.Field(
        column_name="predifined_answers",
        attribute="predifined_answers",
        widget=TranslatedNameM2MWidget(
            PredifinedAnswer, field="predifined_answer", separator="\n"
        ),
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


@admin.register(Question, site=admin_site)
class QuestionAdmin(ImportExportModelAdmin, TranslatableAdmin):
    list_display = ["label", "category", "position", "get_predifined_answers"]
    search_fields = ["label"]
    resource_class = QuestionResource


class RegulationTypeResource(TranslationUpdateMixin, resources.ModelResource):
    label = fields.Field(
        column_name="label",
        attribute="label",
    )

    class Meta:
        model = RegulationType


@admin.register(RegulationType, site=admin_site)
class RegulationTypeAdmin(ImportExportModelAdmin, TranslatableAdmin):
    list_display = ["label"]
    search_fields = ["label"]
    resource_class = RegulationTypeResource


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


@admin.register(Impact, site=admin_site)
class ImpactAdmin(ImportExportModelAdmin, TranslatableAdmin):
    list_display = ["label"]
    search_fields = ["label"]
    resource_class = ImpactResource


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

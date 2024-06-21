from django.contrib import admin
from governanceplatform.mixins import TranslationUpdateMixin
from governanceplatform.admin import admin_site
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin, ExportActionModelAdmin
from parler.admin import TranslatableAdmin
from governanceplatform.widgets import TranslatedNameM2MWidget, TranslatedNameWidget

from securityobjectives.models import (
    Domain,
    Standard,
    MaturityLevel,
    SecurityObejctive
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
        fields = ('label', 'position')


@admin.register(Domain, site=admin_site)
class DomainAdmin(ImportExportModelAdmin, ExportActionModelAdmin, TranslatableAdmin):
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

    class Meta:
        model = Standard
        fields = ('label', 'description')


@admin.register(Standard, site=admin_site)
class StandardAdmin(ImportExportModelAdmin, ExportActionModelAdmin, TranslatableAdmin):
    resource_class = StandardResource
    list_display = [
        "label",
        "description",
    ]


class MaturityLevelResource(TranslationUpdateMixin, resources.ModelResource):
    id = fields.Field(column_name="id", attribute="id", readonly=True)
    label = fields.Field(
        column_name="label",
        attribute="label",
    )

    class Meta:
        model = MaturityLevel
        fields = ('label')


@admin.register(MaturityLevel, site=admin_site)
class MaturityLevelAdmin(ImportExportModelAdmin, ExportActionModelAdmin, TranslatableAdmin):
    resource_class = MaturityLevelResource
    list_display = [
        "label",
    ]


class SecurityObejctiveResource(TranslationUpdateMixin, resources.ModelResource):
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
        model = SecurityObejctive
        fields = ('objective', 'description', 'unique_code', 'position', 'domain', 'standards')


@admin.register(SecurityObejctive, site=admin_site)
class SecurityObejctiveAdmin(ImportExportModelAdmin, ExportActionModelAdmin, TranslatableAdmin):
    resource_class = SecurityObejctiveResource
    list_display = [
        "objective",
        "description",
        "unique_code",
        "position",
        "domain",
    ]

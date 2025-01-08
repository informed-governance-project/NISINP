from django.contrib import admin
from import_export import fields, resources
from import_export.admin import ImportExportModelAdmin

from governanceplatform.admin import CustomTranslatableAdmin, admin_site
from governanceplatform.mixins import TranslationUpdateMixin
from governanceplatform.models import Sector
from governanceplatform.widgets import TranslatedNameM2MWidget
from django.db.models import Count

from .models import ObservationRecommendation


class ObservationRecommendationResource(
    TranslationUpdateMixin, resources.ModelResource
):
    id = fields.Field(
        column_name="id",
        attribute="id",
    )
    code = fields.Field(
        column_name="code",
        attribute="code",
    )
    description = fields.Field(
        column_name="description",
        attribute="description",
    )

    sectors = fields.Field(
        column_name="sectors",
        attribute="sectors",
        widget=TranslatedNameM2MWidget(Sector, field="name", separator="|"),
    )

    class Meta:
        model = ObservationRecommendation
        fields = (
            "id",
            "code",
            "description",
            "sectors",
        )
        export_order = fields


@admin.register(ObservationRecommendation, site=admin_site)
class ObservationRecommendationAdmin(CustomTranslatableAdmin, ImportExportModelAdmin):
    resource_class = ObservationRecommendationResource
    list_display = ["code", "description", "get_sector_name"]
    search_fields = ["code", "description"]
    filter_horizontal = ("sectors",)
    fields = (
        "code",
        "description",
        "sectors",
    )

    @admin.display(description="Sectors")
    def get_sector_name(self, obj):
        return [sector for sector in obj.sectors.all()]

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "sectors":
            # exclude parent with children from the list
            kwargs["queryset"] = Sector.objects.annotate(
                child_count=Count("children")
            ).exclude(parent=None, child_count__gt=0)

        return super().formfield_for_manytomany(db_field, request, **kwargs)

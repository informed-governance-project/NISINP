from django.contrib.auth.models import Group
from django.contrib import admin
from django.core.exceptions import ObjectDoesNotExist
from import_export import fields, resources
from import_export.admin import ImportExportModelAdmin

from governanceplatform.admin import (
    CustomTranslatableAdmin,
    admin_site,
)

from governanceplatform.mixins import TranslationUpdateMixin
from .models import (  # OperatorType,; Service,
    ObservationRecommendation
)


# get the id of a group by name
def get_group_id(name=""):
    try:
        group_id = Group.objects.get(name=name).id
    except ObjectDoesNotExist:
        group_id = None

    return group_id


class ObservationRecommendationResource(TranslationUpdateMixin, resources.ModelResource):
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

    def after_import_instance(self, instance, new, row_number=None, **kwargs):
        if instance:
            instance.is_generic = True

    class Meta:
        model = ObservationRecommendation


@admin.register(ObservationRecommendation, site=admin_site)
class ObservationRecommendationAdmin(CustomTranslatableAdmin, ImportExportModelAdmin):
    list_display = ["code", "description"]
    search_fields = ["code", "description"]
    resource_class = ObservationRecommendationResource
    fields = (
        "description",
        "code",
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.filter(is_generic=True)

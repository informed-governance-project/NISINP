import django_filters
from .models import Incident, SectorRegulation
from governanceplatform.models import Sector
from .forms import IncidentWorkflowForm, IncidentStatusForm
from django.db.models.functions import Concat
from django.db.models import Case, Value, When
from django.utils.translation import get_language


# define a tree view for the sectors (only work with 2 levels)
# Only fetch on the current language
def affected_sectors(request):

    return Sector.objects.translated(get_language()).annotate(
        full_name=Case(
            When(parent__isnull=False, then=Concat('parent__translations__name', Value(' --> '), 'translations__name')),
            default='translations__name',
        )
    ).order_by('full_name')


# define specific query to get the regulation
# TO DO : the returned value is not correct
def sector_regulation(request):
    return SectorRegulation.objects.all().values_list('regulation__translations__label', flat=True).distinct()


class IncidentFilter(django_filters.FilterSet):
    incident_id = django_filters.CharFilter(lookup_expr='icontains')
    affected_sectors = django_filters.ModelChoiceFilter(queryset=affected_sectors)
    sector_regulation = django_filters.ModelChoiceFilter(queryset=sector_regulation)

    class Meta:
        model = Incident
        fields = [
            "incident_id",
            "incident_status",
            "is_significative_impact",
            "affected_sectors",
            "sector_regulation"
        ]

    # Needed to add the form for modification of
    # incident_id, incident_status and significative impact
    @property
    def qs(self):
        parent = super().qs

        for incident in parent:
            incident.formsWorkflow = []
            for workflow_completed in incident.get_workflows_completed():
                incident.formsWorkflow.append(
                    IncidentWorkflowForm(instance=workflow_completed)
                )
            incident.formsStatus = IncidentStatusForm(
                instance=incident,
            )

        return parent

import django_filters

from .forms import IncidentStatusForm, IncidentWorkflowForm
from .models import Incident


class IncidentFilter(django_filters.FilterSet):
    incident_id = django_filters.CharFilter(lookup_expr="iexact")

    class Meta:
        model = Incident
        fields = ["incident_id", "incident_status"]

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

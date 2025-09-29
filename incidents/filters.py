import django_filters
from django.db.models import F, Q
from django.utils.translation import gettext as _

from governanceplatform.models import Sector

from .forms import DropdownCheckboxSelectMultiple
from .models import Incident, SectorRegulation


# define specific query to get the regulation
def sector_regulation(request):
    return SectorRegulation.objects.distinct()


class IncidentFilter(django_filters.FilterSet):
    incident_id = django_filters.CharFilter(lookup_expr="icontains")
    affected_sectors = django_filters.ModelMultipleChoiceFilter(
        queryset=Sector.objects.filter(
            ~Q(
                id__in=Sector.objects.exclude(parent=None).values_list(
                    "parent_id", flat=True
                )
            )
            | Q(id=F("parent_id"))
        ).order_by("parent"),
        widget=DropdownCheckboxSelectMultiple(
            attrs={"data-selected-text-format": "count > 2"}
        ),
    )
    sector_regulation = django_filters.ModelChoiceFilter(queryset=sector_regulation)

    search = django_filters.CharFilter(method="filter_search", label=_("Search"))

    class Meta:
        model = Incident
        fields = [
            "incident_id",
            "incident_status",
            "is_significative_impact",
            "affected_sectors",
            "sector_regulation",
        ]

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(incident_id__icontains=value)
            | Q(contact_firstname__icontains=value)
            | Q(contact_lastname__icontains=value)
            | Q(technical_firstname__icontains=value)
            | Q(technical_lastname__icontains=value)
            | Q(company_name__icontains=value)
            | Q(company__identifier__icontains=value)
            | Q(company__name__icontains=value)
            | Q(regulator__translations__name__icontains=value)
            | Q(regulator__translations__full_name__icontains=value)
            | Q(sector_regulation__regulation__translations__label__icontains=value)
            | Q(affected_sectors__translations__name__icontains=value)
        ).distinct()

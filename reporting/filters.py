import django_filters
from django.db.models import F, Q
from django.utils import timezone

from governanceplatform.models import Company, Sector
from incidents.forms import DropdownCheckboxSelectMultiple


class YearChoiceFilter(django_filters.ChoiceFilter):
    def filter(self, qs, value):
        return qs


class CompanyFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(
        lookup_expr="icontains",
        label="Name",
    )

    year = YearChoiceFilter(
        label="Year",
        choices=[
            (year, year)
            for year in range(timezone.now().year - 2, timezone.now().year + 1)
        ],
    )

    sectors = django_filters.ModelMultipleChoiceFilter(
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
        method="filter_by_sector",
        label="Sectors",
    )

    class Meta:
        model = Company
        fields = [
            "name",
        ]

    def filter_by_sector(self, queryset, name, value):
        if not value:
            return queryset

        sector_ids = [sector.id for sector in value]

        filtered_company_ids = [
            company.id
            for company in queryset
            if any(sector.id in sector_ids for sector in company.get_queryset_sectors())
        ]

        return queryset.filter(id__in=filtered_company_ids)

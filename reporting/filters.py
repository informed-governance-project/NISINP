import django_filters
from django.db.models import F, Q

from governanceplatform.models import Company, Sector
from incidents.forms import DropdownCheckboxSelectMultiple


class CompanyFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(
        lookup_expr="icontains",
        label="Name",
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

    # def __init__(self, *args, **kwargs):
    #     queryset = kwargs.get("queryset", StandardAnswer.objects.none())
    #     super().__init__(*args, **kwargs)
    #     submitter_user_ids = set(queryset.values_list("submitter_user", flat=True))

    #     submitter_companies_ids = set(
    #         queryset.values_list("submitter_company", flat=True)
    #     )

    #     self.filters["submitter_user"].queryset = User.objects.filter(
    #         id__in=submitter_user_ids
    #     )

    #     self.filters["submitter_company"].queryset = Company.objects.filter(
    #         id__in=submitter_companies_ids
    # )

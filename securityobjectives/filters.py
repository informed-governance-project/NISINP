import django_filters
from django.db.models import F, Q
from django.utils.translation import gettext as _

from governanceplatform.models import Company, Sector, User
from incidents.forms import DropdownCheckboxSelectMultiple

from .models import StandardAnswer


class YearChoiceFilter(django_filters.ChoiceFilter):
    def filter(self, qs, value):
        if value:
            return qs.filter(year_of_submission=value)
        return qs


class StandardAnswerFilter(django_filters.FilterSet):
    year_of_submission = YearChoiceFilter()
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
    )
    search = django_filters.CharFilter(method="filter_search", label=_("Search"))

    class Meta:
        model = StandardAnswer
        fields = [
            "standard",
            "status",
            "submitter_user",
            "submitter_company",
            "year_of_submission",
            "sectors",
        ]

    def __init__(self, *args, **kwargs):
        queryset = kwargs.get("queryset", StandardAnswer.objects.none())
        super().__init__(*args, **kwargs)
        submitter_user_ids = set(queryset.values_list("submitter_user", flat=True))

        submitter_companies_ids = set(
            queryset.values_list("submitter_company", flat=True)
        )

        self.filters["submitter_user"].queryset = User.objects.filter(
            id__in=submitter_user_ids
        )

        self.filters["submitter_company"].queryset = Company.objects.filter(
            id__in=submitter_companies_ids
        )

        years = set(self.queryset.values_list("year_of_submission", flat=True))
        self.filters["year_of_submission"].extra["choices"] = [
            (year, year) for year in sorted(years)
        ]

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(standard__translations__label__icontains=value)
            | Q(standard__translations__description__icontains=value)
            | Q(creator_name__icontains=value)
            | Q(submitter_company__name__icontains=value)
            | Q(year_of_submission__icontains=value)
            | Q(sectors__translations__name__icontains=value)
        ).distinct()

import django_filters
from django.db.models import F, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from governanceplatform.models import Company, Sector, User
from incidents.forms import DropdownCheckboxSelectMultiple

from .models import CompanyProject, ObservationRecommendation, Project


class YearChoiceFilter(django_filters.ChoiceFilter):
    def filter(self, qs, value):
        return qs


class CompanyFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(
        lookup_expr="icontains",
        label=_("Operator"),
    )

    year = YearChoiceFilter(
        label=_("Year"),
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
        label=_("Sectors"),
    )

    search = django_filters.CharFilter(method="filter_search", label=_("Search"))

    class Meta:
        model = Company
        fields = [
            "name",
        ]

    def filter_by_sector(self, queryset, name, value):
        return queryset

    def filter_search(self, queryset, name, value):
        return queryset


class RecommendationFilter(django_filters.FilterSet):
    code = django_filters.CharFilter(
        lookup_expr="icontains",
        label=_("Name"),
    )

    description = django_filters.CharFilter(
        lookup_expr="icontains",
        field_name="translations__description",
        label=_("Description"),
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
        label=_("Sectors"),
    )

    class Meta:
        model = ObservationRecommendation
        fields = ["code", "description", "sectors"]

    def filter_by_sector(self, queryset, name, value):
        if not value:
            return queryset

        sector_ids = [sector.id for sector in value]

        return queryset.filter(Q(sectors__in=sector_ids) | Q(sectors=None)).distinct()


class ProjectFilter(django_filters.FilterSet):
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
        model = Project
        fields = [
            "standard",
            "sectors",
            "author",
            "name",
            # "years",
        ]

    def __init__(self, *args, **kwargs):
        queryset = kwargs.get("queryset", Project.objects.none())
        super().__init__(*args, **kwargs)
        submitter_user_ids = set(queryset.values_list("author", flat=True))

        self.filters["author"].queryset = User.objects.filter(id__in=submitter_user_ids)

        # years = set(self.queryset.values_list("years", flat=True))
        # self.filters["years"].extra["choices"] = [
        #     (year, year) for year in sorted(years)
        # ]

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(standard__translations__label__icontains=value)
            | Q(standard__translations__description__icontains=value)
            | Q(author__icontains=value)
            # | Q(years__icontains=value)
            | Q(sectors__translations__name__icontains=value)
            | Q(name__icontains=value)
        ).distinct()


class CompanyProjectFilter(django_filters.FilterSet):
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
        model = CompanyProject
        fields = [
            "company",
            "sector",
            "year",
        ]

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(company__name__icontains=value)
            | Q(year__icontains=value)
            | Q(sector__translations__name__icontains=value)
        ).distinct()

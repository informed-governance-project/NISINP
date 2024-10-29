import django_filters

from .models import StandardAnswer


class StandardAnswerFilter(django_filters.FilterSet):
    class Meta:
        model = StandardAnswer
        fields = [
            "standard",
            "standard_notification_date",
            "status",
            "submitter_company",
            "year_of_submission",
        ]

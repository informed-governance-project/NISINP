import pytest
from django.utils.translation import activate

from securityobjectives.models import (
    Domain,
    MaturityLevel,
    SecurityMeasure,
    SecurityObjective,
    SecurityObjectivesInStandard,
    Standard,
)


@pytest.mark.django_db
def test_so_elements_in_db(populate_so_db):
    """
    Check if objects are present in DB
    """
    activate("en")
    assert Standard.objects.count() == 1
    assert MaturityLevel.objects.count() == 4
    assert Domain.objects.count() == 8
    assert SecurityMeasure.objects.count() == 174
    assert SecurityObjective.objects.count() == 29
    assert SecurityObjectivesInStandard.objects.count() == 29

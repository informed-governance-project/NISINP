import pytest
from django.utils.translation import activate

from incidents.models import (
    Email,
    Impact,
    PredefinedAnswer,
    Question,
    QuestionCategory,
    QuestionCategoryOptions,
    QuestionOptions,
    SectorRegulation,
    SectorRegulationWorkflow,
    Workflow,
)


@pytest.mark.django_db
def test_incidents_elements_in_db(populate_incident_db):
    """
    Check if objects are present in DB
    """
    activate("en")
    assert Email.objects.count() == 4
    assert Question.objects.count() == 10
    assert QuestionCategory.objects.count() == 4
    assert PredefinedAnswer.objects.count() == 8
    assert Workflow.objects.count() == 4
    assert QuestionCategoryOptions.objects.count() == 4
    assert QuestionOptions.objects.count() == 10
    assert SectorRegulation.objects.count() == 2
    assert SectorRegulationWorkflow.objects.count() == 4
    assert Impact.objects.count() == 3

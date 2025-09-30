import pytest
from django.utils.translation import activate
from governanceplatform.models import (
    Company,
    Regulator,
    Observer,
    EntityCategory,
)
from django_countries.fields import Country


@pytest.fixture
def populate_db(db):
    """
    Populate the DB
    """

    # Force default language for translatable
    activate("en")

    # Dependencies M2M
    entity_category = EntityCategory.objects.create(label="Critical")

    # Create a company
    company = Company.objects.create(
        identifier="CO01",
        name="Test Company",
        country=Country("FR"),
        address="123 Rue de Paris",
        email="contact@testcompany.com",
        phone_number="+33123456789",
    )
    company.entity_categories.add(entity_category)

    # Create a regulator
    regulator = Regulator.objects.create(
        country=Country("FR"),
        address="10 Avenue de la République",
        email_for_notification="notify@regulator.com",
    )
    regulator.set_current_language("en")
    regulator.name = "Regulator lu"
    regulator.full_name = "LU National Regulator"
    regulator.description = "Responsible for national telecom regulation"
    regulator.save()

    # Create an observer
    observer = Observer.objects.create(
        country=Country("BE"),
        address="56 Boulevard de Bruxelles",
        email_for_notification="observer@belgium.org",
        is_receiving_all_incident=True,
    )
    observer.name = "Observer BE"
    observer.full_name = "Belgian Observer"
    observer.description = "Observer entity for incidents"
    observer.save()

    return {
        "company": company,
        "regulator": regulator,
        "observer": observer,
        "entity_category": entity_category,
    }

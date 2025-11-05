import pytest
from django.contrib.auth.models import Group
from django.utils import timezone
from django.utils.translation import activate

from conftest import import_from_json
from governanceplatform.models import (
    Company,
    EntityCategory,
    Functionality,
    Observer,
    Regulation,
    Regulator,
    Sector,
    User,
)
from governanceplatform.permissions import update_all_group_permissions
from governanceplatform.tests.data import (
    companies_data,
    functionalities_data,
    observers_data,
    permission_groups,
    regulations,
    regulators_data,
    sectors,
    users,
)


@pytest.fixture
def populate_db(db):
    """
    Populate the DB
    """

    # Force default language for translatable
    activate("en")

    # Dependencies M2M
    entity_category = EntityCategory.objects.create(label="Critical")

    # Create companies
    created_companies = import_from_json(Company, companies_data)

    # Create functionnality
    created_functionalities = import_from_json(Functionality, functionalities_data)

    # Create regulators
    created_regulators = import_from_json(Regulator, regulators_data)

    # Create an observer
    created_observers = import_from_json(Observer, observers_data)

    # Create permission groups
    created_permission_groups = import_from_json(Group, permission_groups)

    # Create sectors
    created_sectors = import_from_json(Sector, sectors)

    # Create regulations
    created_regulations = import_from_json(Regulation, regulations)

    # Create users
    created_users = import_from_json(User, users)
    # special set for user and permissions
    initialize_user(created_users)
    link_entity_user(users, created_users)
    update_all_group_permissions()

    return {
        "companies": created_companies,
        "functionnalities": created_functionalities,
        "regulators": created_regulators,
        "observers": created_observers,
        "entity_categories": [entity_category],
        "permissions_groups": created_permission_groups,
        "sectors": created_sectors,
        "regulations": created_regulations,
        "users": created_users,
    }


def initialize_user(users):
    for user in users:
        user.accepted_terms_date = timezone.now()
        user.save()


def link_entity_user(raw_data, created_users):
    for user in raw_data:
        if "email" in user:
            user_db = User.objects.filter(email=user["email"]).first()
            if "companies" in user and user_db:
                for c in user["companies"]:
                    if "identifier" in c:
                        company_db = Company.objects.get(identifier=c["identifier"])
                        user_db.companies.add(company_db)
                user_db.save()

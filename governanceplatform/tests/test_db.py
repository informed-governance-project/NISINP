import pytest
from django.contrib.auth.models import Group
from django.db import OperationalError, connection
from django.utils.translation import activate

from governanceplatform.models import (
    Company,
    Functionality,
    Observer,
    Regulation,
    Regulator,
    Sector,
    User,
)


# poetry run pytest governanceplatform/tests/test_db.py
@pytest.mark.django_db
def test_database_connection(db):
    """
    Check the database connection
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            row = cursor.fetchone()
        assert row[0] == 1  # DB doesn't send the correct value
    except OperationalError as e:
        assert e is None  # DB is not accessible


@pytest.mark.django_db
def test_elements_in_db(populate_db):
    """
    Check if objects are present in DB
    """
    activate("en")
    assert Company.objects.count() == 2
    assert Functionality.objects.count() == 2
    assert Regulator.objects.count() == 2
    assert Observer.objects.count() == 1
    assert Group.objects.count() == 8
    assert Sector.objects.count() == 7
    assert Regulation.objects.count() == 2
    assert User.objects.count() == 12

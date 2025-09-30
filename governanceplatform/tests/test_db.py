import pytest
from django.db import connection, OperationalError
from governanceplatform.models import (
    Company,
    Regulator,
    Observer,
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
    assert Company.objects.count() >= 1
    assert Regulator.objects.count() >= 1
    assert Observer.objects.count() >= 1

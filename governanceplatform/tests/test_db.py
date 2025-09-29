from django.test import TestCase
from django.db import connection, OperationalError


# poetry run python manage.py test governanceplatform.tests.test_db
class DatabaseConnectionTest(TestCase):
    def test_database_connection(self):
        """
        Check the database connection
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1;")
                row = cursor.fetchone()
            self.assertEqual(row[0], 1, "The DB doesn't send back the right value")
        except OperationalError as e:
            self.fail(f"Connection failed : {e}")

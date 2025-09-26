from django.test import TestCase
from django.urls import reverse


# poetry run python manage.py test governanceplatform.tests.test_views
class UrlAccess(TestCase):
    restricted_names = [
        "admin:index",
        "edit_account",
        "incidents",
        "logout",
        "set_language",
        "contact",
    ]

    non_restricted_urls = [
        "privacy",
        "cookies",
        "sitemap",
        "accessibility",
        "registration",
        "login",
    ]

    """
    Test if a non logged-in user can access to restricted views
    """
    def test_restricted_urls_without_credential(self):
        for name in self.restricted_names:
            url = reverse(name)
            response = self.client.get(url)
            self.assertEqual(
                response.status_code, 302,
                f"The URL '{name}' Should get a 302 if a user is not connected."
            )

    """
    Test if a non logged-in user can access the non restricted URLS
    """
    def test_accessible_urls_without_credential(self):
        for name in self.non_restricted_urls:
            url = reverse(name)
            response = self.client.get(url)
            self.assertEqual(
                response.status_code, 200,
                f"The URL '{name}' Should get a 200 if a user is not connected."
            )

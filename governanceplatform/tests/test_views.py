import pytest
from django.urls import reverse
from governanceplatform.helpers import user_in_group
from django.utils.timezone import now

# Restricted URL
restricted_names = [
    "admin:index",
    "edit_account",
    "incidents",
    "logout",
    "set_language",
    "contact",
]

# Public URL
non_restricted_urls = [
    "privacy",
    "cookies",
    "sitemap",
    "accessibility",
    "registration",
    "login",
]


@pytest.mark.django_db
def test_restricted_urls_without_credential(client):
    """
    Verify that a user who is not logged in is redirected to restricted views.
    """
    for name in restricted_names:
        url = reverse(name)
        response = client.get(url)
        assert response.status_code == 302


@pytest.mark.django_db
def test_accessible_urls_without_credential(client):
    """
    Verify that a user who is not logged in can access public pages.
    """
    for name in non_restricted_urls:
        url = reverse(name)
        response = client.get(url)
        assert response.status_code == 200


@pytest.mark.django_db
def test_user_access_admin(client, populate_db):
    """
    Verify that a user in the IncidentUser group or OperatorUser group cannot access the admin
    """
    users = populate_db["users"]

    for user in users:
        user.refresh_from_db()
        user.accepted_terms_date = now().date()
        user.save()
        client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')
        # print(user)
        # print(user.is_authenticated)
        # print(user.is_staff)
        # print(user.is_active)
        # print(user.groups.all())
        # print(user.regulators.all())
        # print(user.get_all_permissions())

        if user_in_group(user, "IncidentUser") or user_in_group(user, "OperatorUser"):
            print("coucou")
            url = reverse("admin:index")
            response = client.get(url)
            assert response.status_code in (302, 403), (
                f"User {user.email} should not access to the admin"
            )
        if user_in_group(user, "RegulatorAdmin"):
            url = reverse("admin:index")
            response = client.get(url)
            assert response.status_code == 200, (
                f"User {user.email} should access to the admin"
            )

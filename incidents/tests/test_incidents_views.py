import pytest

from conftest import list_admin_add_urls, list_url_freetext_filter
from governanceplatform.helpers import user_in_group


@pytest.mark.django_db
def test_incident_user_access_without_2FA(client, populate_db):
    """
    Verify if the incident main pages are not accessible without 2FA
    """
    users = populate_db["users"]

    for user in users:
        client.force_login(user)
        url_list = list_url_freetext_filter("incidents", "admin")
        for url in url_list:
            response = client.get("/" + url)
            print(url)
            assert response.status_code in (
                302,
                403,
            ), f"User {user.email} should not access to the admin without 2FA"


@pytest.mark.django_db
def test_incidents_admin_roles_addition_rights(otp_client, populate_db):
    """
    Test the rights of each groups on the model of incidents
    """
    users = populate_db["users"]
    regulator_admin_rights = [
        "email",
        "impact",
        "sectorregulation",
        "workflow",
        "question",
        "sectorregulationworkflowemail",
        "predefinedanswer",
    ]
    for user in users:
        client = otp_client(user)
        for u in list_admin_add_urls("incidents"):
            if user_in_group(user, "RegulatorAdmin") and any(
                model in u for model in regulator_admin_rights
            ):
                response = client.get("/" + u)
                assert response.status_code == 200
            else:
                response = client.get("/" + u)
                assert response.status_code in (302, 403, 404)

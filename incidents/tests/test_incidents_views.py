import pytest
from django.utils import timezone

from conftest import list_admin_add_urls, list_url_freetext_filter
from governanceplatform.helpers import (
    can_access_incident,
    is_user_operator,
    is_user_regulator,
    user_in_group,
)
from governanceplatform.models import RegulatorUser
from governanceplatform.settings import TIME_ZONE
from incidents.models import Incident


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


@pytest.fixture
def create_incident():
    """
    Fixture to create an incident
    """

    def _create_incident(
        user,
        workflow,
        sectors=None,
        impacts=None,
        is_significative_impact=False,
        incident_id="",
        incident_detection_date=timezone.now,
    ):
        incident = Incident.objects.create(
            incident_id=incident_id,
            incident_timezone=TIME_ZONE,
            incident_detection_date=incident_detection_date,
            company=user.companies.first() if is_user_operator(user) else None,
            regulator=user.regulators.first() if is_user_regulator(user) else None,
            contact_user=user,
            sector_regulation=workflow,
            is_significative_impact=is_significative_impact,
        )
        if sectors:
            incident.affected_sectors.set(sectors)
        if impacts:
            incident.impacts.set(impacts)
        incident.save()
        return incident

    return _create_incident


@pytest.mark.django_db(transaction=True)
def test_pdf_download_of_operator_incident(otp_client, populate_db, create_incident):
    """
    Test if the PDF download is accessible to the right users
    """
    users = populate_db["users"]
    workflows = populate_db["incidents_workflows"]
    # operator admin
    user = next((u for u in users if u.email == "opadmin@com1.lu"), None)
    authorized_users = [
        u
        for u in users
        if u.email == "opadmin@com1.lu"
        or u.email == "obsadm@cert1.lu"  # receive all incident
        or u.email == "opuser@com1.lu"
        or u.email == "regadmin@reg1.lu"
    ]
    # asectorial workflow
    workflow = next((u for u in workflows if u.id == 1), None)
    incident = create_incident(
        user=user,
        workflow=workflow,
        sectors=None,
        impacts=None,
        is_significative_impact=False,
        incident_id="XXXX-SSS-SSS-0001-2005",
        incident_detection_date=timezone.now(),
    )
    assert Incident.objects.count() == 1

    for u in users:
        client = otp_client(u)
        response = client.get("/incidents/download-pdf/" + str(incident.id))

        if u in authorized_users:
            assert response.status_code == 200
        else:
            assert response.status_code in (302, 403)

    # Add a sector to test RegUser see the incident
    sectors = populate_db["sectors"]
    sector = next((u for u in sectors if u.acronym == "ELEC"), None)
    if sector:
        incident.affected_sectors.add(sector)
        incident.save()
        regulator_user = next((u for u in users if u.email == "reguser@reg1.lu"), None)
        ru = RegulatorUser.objects.get(
            user=regulator_user, regulator=regulator_user.regulators.first()
        )
        if ru:
            authorized_users.append(regulator_user)
            ru.sectors.add(sector)
            for u in users:
                client = otp_client(u)
                response = client.get("/incidents/download-pdf/" + str(incident.id))

                if u in authorized_users:
                    assert response.status_code == 200
                else:
                    assert response.status_code in (302, 403)


@pytest.mark.django_db(transaction=True)
def test_can_access_incident_function(populate_db, create_incident):
    """
    Test teh can access incident function
    """
    users = populate_db["users"]
    workflows = populate_db["incidents_workflows"]
    # operator admin
    user = next((u for u in users if u.email == "opadmin@com1.lu"), None)
    authorized_users = [
        u
        for u in users
        if u.email == "opadmin@com1.lu"
        or u.email == "obsadm@cert1.lu"  # receive all incident
        or u.email == "opuser@com1.lu"
        or u.email == "regadmin@reg1.lu"
    ]
    # asectorial workflow
    workflow = next((u for u in workflows if u.id == 1), None)
    incident = create_incident(
        user=user,
        workflow=workflow,
        sectors=None,
        impacts=None,
        is_significative_impact=False,
        incident_id="XXXX-SSS-SSS-0001-2005",
        incident_detection_date=timezone.now(),
    )
    assert Incident.objects.count() == 1

    for u in users:
        company = -1
        if u.companies.first() is not None:
            company = u.companies.first().id
        if u in authorized_users:
            assert can_access_incident(u, incident, company) is True
        else:
            assert can_access_incident(u, incident, company) is False

    # Add a sector to test RegUser see the incident
    sectors = populate_db["sectors"]
    sector = next((u for u in sectors if u.acronym == "ELEC"), None)
    if sector:
        incident.affected_sectors.add(sector)
        incident.save()
        regulator_user = next((u for u in users if u.email == "reguser@reg1.lu"), None)
        ru = RegulatorUser.objects.get(
            user=regulator_user, regulator=regulator_user.regulators.first()
        )
        if ru:
            authorized_users.append(regulator_user)
            ru.sectors.add(sector)
            for u in users:
                company = -1
                if u.companies.first() is not None:
                    company = u.companies.first().id
                if u in authorized_users:
                    assert can_access_incident(u, incident, company) is True
                else:
                    assert can_access_incident(u, incident, company) is False

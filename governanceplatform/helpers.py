import secrets
from typing import Optional

from .models import Company, User
from incidents.models import Incident


def generate_token():
    """Generates a random token-safe text string."""
    return secrets.token_urlsafe(32)[:32]


def user_in_group(user, group_name) -> bool:
    """Check user group"""
    if not user.is_authenticated:
        return False
    return any(user_group.name == group_name for user_group in user.groups.all())


def is_user_regulator(user: User) -> bool:
    return user_in_group(user, "RegulatorAdmin") or user_in_group(user, "RegulatorUser")


def is_cert_user(user: User) -> bool:
    return user_in_group(user, "CertAdmin") or user_in_group(user, "CertUser")


def is_cert_user_viewving_all_incident(user: User) -> bool:
    return (user_in_group(user, "CertAdmin") or user_in_group(user, "CertUser")) and user.certs.first().is_receiving_all_incident


def get_active_company_from_session(request) -> Optional[Company]:
    company_in_use = request.session.get("company_in_use")
    return request.user.companies.get(id=company_in_use) if company_in_use else None


def can_access_incident(user: User, incident: Incident, company_id=-1) -> bool:
    # RegulatorUser can access only incidents from accessible sectors.
    if (
        user_in_group(user, "RegulatorUser")
        and Incident.objects.filter(
            pk=incident.id, affected_services__sector__in=user.sectors.all()
        ).exists()
    ):
        return True
    # OperatorAdmin can access only incidents related to selected company.
    if (
        user_in_group(user, "OperatorAdmin")
        and Incident.objects.filter(
            pk=incident.id, company__id=company_id
        ).exists()
    ):
        return True
    # OperatorStaff and IncidentUser can access only their reports.
    if (
        not is_user_regulator(user)
        and (user_in_group(user, "OperatorUser") or user_in_group(user, "IncidentUser"))
        and Incident.objects.filter(
            pk=incident.id, contact_user=user
        ).exists()
    ):
        return True
    # CertUser access all incident if he is in a cert who can access all incident.
    if is_cert_user_viewving_all_incident(user):
        return True

    return False


# check if the user is allowed to create an incident_workflow
def can_create_incident_report(user: User, incident: Incident, company_id=-1) -> bool:
    # prevent regulator and cert to create incident_workflow
    if (
        user_in_group(user, "RegulatorUser")
        or user_in_group(user, "RegulatorAdmin")
        or user_in_group(user, "CertAdmin")
        or user_in_group(user, "CertUser")
        or user_in_group(user, "PlatformAdmin")
    ):
        return False
    # if it's the incident of the user he can create
    if (incident.contact_user == user):
        return True
    # if he is admin of the company he can create
    if (
        user_in_group(user, "OperatorAdmin")
        and Incident.objects.filter(
            pk=incident.id, company__id=company_id
        ).exists()
    ):
        return True
    return False

import secrets
from typing import Optional

from django.db import connection

from incidents.models import Incident

from .models import Company, User


def table_exists(table_name: str) -> bool:
    """Checks if a table exists."""
    all_tables = connection.introspection.table_names()
    return table_name in all_tables


def generate_token():
    """Generates a random token-safe text string."""
    return secrets.token_urlsafe(32)[:32]


def user_in_group(user, group_name) -> bool:
    """Check user group"""
    if not user.is_authenticated:
        return False
    return any(user_group.name == group_name for user_group in user.groups.all())


def instance_user_in_group(user_instance, group_name) -> bool:
    return any(
        user_group.name == group_name for user_group in user_instance.groups.all()
    )


def is_user_regulator(user: User) -> bool:
    return user_in_group(user, "RegulatorAdmin") or user_in_group(user, "RegulatorUser")


def is_observer_user(user: User) -> bool:
    return user_in_group(user, "ObserverAdmin") or user_in_group(user, "ObserverUser")


def is_observer_user_viewving_all_incident(user: User) -> bool:
    return (
        user_in_group(user, "ObserverAdmin") or user_in_group(user, "ObserverUser")
    ) and user.observers.first().is_receiving_all_incident


def get_active_company_from_session(request) -> Optional[Company]:
    company_in_use = request.session.get("company_in_use")
    return request.user.companies.filter(id=company_in_use).first() if company_in_use else None


def can_access_incident(user: User, incident: Incident, company_id=-1) -> bool:
    # RegulatorUser can access only incidents from accessible sectors.
    if (
        user_in_group(user, "RegulatorUser")
        and Incident.objects.filter(
            pk=incident.id, sector_regulation__regulator=user.regulators.first()
        ).exists()
    ):
        sectors = [
            sector
            for sector in incident.affected_sectors.all()
            if sector in user.get_sectors().all()
        ]
        if len(sectors) > 0:
            return True
        else:
            return False
    # RegulatorAdmin can access only incidents from accessible regulators.
    if (
        user_in_group(user, "RegulatorAdmin")
        and Incident.objects.filter(
            pk=incident.id, sector_regulation__regulator=user.regulators.first()
        ).exists()
    ):
        return True
    # OperatorAdmin can access only incidents related to selected company.
    if (
        user_in_group(user, "OperatorAdmin")
        and Incident.objects.filter(pk=incident.id, company__id=company_id).exists()
    ):
        return True
    # OperatorUser can access incidents related to selected company and sectors
    if (
        user_in_group(user, "OperatorUser")
        and Incident.objects.filter(
            pk=incident.id,
            company__id=company_id,
            affected_sectors__in=user.sectors.all(),
        ).exists()
    ):
        return True
    # OperatorStaff and IncidentUser can access their reports.
    if (
        not is_user_regulator(user)
        and (user_in_group(user, "OperatorUser") or user_in_group(user, "IncidentUser"))
        and Incident.objects.filter(pk=incident.id, contact_user=user).exists()
    ):
        return True
    # ObserverUser access all incident if he is in a observer who can access all incident.
    if is_observer_user_viewving_all_incident(user):
        return True

    return False


# check if the user is allowed to create an incident_workflow
def can_create_incident_report(user: User, incident: Incident, company_id=-1) -> bool:
    # prevent regulator and observer to create incident_workflow
    if (
        user_in_group(user, "RegulatorUser")
        or user_in_group(user, "RegulatorAdmin")
        or user_in_group(user, "ObserverAdmin")
        or user_in_group(user, "ObserverUser")
        or user_in_group(user, "PlatformAdmin")
    ):
        return False
    # if it's the incident of the user he can create
    if incident.contact_user == user:
        return True
    # if it's in his sector and user of the company
    if (
        user_in_group(user, "OperatorUser")
        and Incident.objects.filter(
            pk=incident.id,
            company__id=company_id,
            affected_sectors__in=user.sectors.all(),
        ).exists()
    ):
        return True
    # if he is admin of the company he can create
    if (
        user_in_group(user, "OperatorAdmin")
        and Incident.objects.filter(pk=incident.id, company__id=company_id).exists()
    ):
        return True
    return False


# check if the user is allowed to edit an incident_workflow
# for regulators to add message
def can_edit_incident_report(user: User, incident: Incident, company_id=-1) -> bool:
    # prevent platform admin
    if user_in_group(user, "PlatformAdmin"):
        return False
    # if it's the incident of the user he can create
    if incident.contact_user == user:
        return True
    # if it's in his sector and user of the company
    if (
        user_in_group(user, "OperatorUser")
        and Incident.objects.filter(
            pk=incident.id,
            company__id=company_id,
            affected_sectors__in=user.sectors.all(),
        ).exists()
    ):
        return True
    # if he is admin of the company he can create
    if (
        user_in_group(user, "OperatorAdmin")
        and Incident.objects.filter(pk=incident.id, company__id=company_id).exists()
    ):
        return True
    # if he is the regulator admin of the incident need to be link to his regulator
    if (
        user_in_group(user, "RegulatorAdmin")
        and incident.sector_regulation.regulator == user.regulators.first()
    ):
        return True
    # if he is the regulator user of the incident, he need to have the sectors
    if (
        user_in_group(user, "RegulatorUser")
        and incident.sector_regulation.regulator == user.regulators.first()
    ):
        sectors = [
            sector
            for sector in incident.affected_sectors.all()
            if sector in user.get_sectors().all()
        ]
        if len(sectors) > 0:
            return True
        else:
            return False

    return False

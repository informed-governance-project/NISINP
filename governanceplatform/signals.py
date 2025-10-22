from datetime import date
from threading import local

from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import Group
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.contrib.sessions.models import Session
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_delete, post_save, pre_delete, pre_save
from django.dispatch import receiver
from django.utils.timezone import now

from governanceplatform.models import User

from .helpers import user_in_group
from .models import CompanyUser, ObserverUser, PasswordUserHistory, RegulatorUser
from .permissions import (
    set_incident_user_permissions,
    set_observer_admin_permissions,
    set_observer_user_permissions,
    set_operator_admin_permissions,
    set_operator_user_permissions,
    set_regulator_admin_permissions,
    set_regulator_staff_permissions,
)

_thread_locals = local()
_thread_locals.deleting_users = set()


@receiver(pre_save, sender=User)
def save_old_password(sender, instance, **kwargs):
    if instance.pk:
        try:
            user = User.objects.get(pk=instance.pk)
            if user.password != instance.password:
                PasswordUserHistory.objects.create(
                    user=user, hashed_password=user.password
                )
        except User.DoesNotExist:
            pass


# Add logs for user connection
def add_log_for_connection(sender, user, request, **kwargs):
    if (
        user_in_group(user, "RegulatorAdmin")
        or user_in_group(user, "RegulatorUser")
        or user_in_group(user, "PlatformAdmin")
    ):
        LogEntry.objects.log_actions(
            user_id=user.id,
            queryset=User.objects.filter(id=user.id),
            action_flag=5,
        )


user_logged_in.connect(add_log_for_connection)


# Add logs for user deconnection
def log_user_logout(sender, request, user, **kwargs):
    if (
        user_in_group(user, "RegulatorAdmin")
        or user_in_group(user, "RegulatorUser")
        or user_in_group(user, "PlatformAdmin")
    ):
        LogEntry.objects.log_actions(
            user_id=user.id,
            queryset=User.objects.filter(id=user.id),
            action_flag=6,
        )


user_logged_out.connect(log_user_logout)


@receiver(post_save, sender=CompanyUser)
def update_user_groups(sender, instance, created, **kwargs):
    user = instance.user
    user.is_staff = False
    user.is_superuser = False

    some_company_is_administrator = user.companyuser_set.filter(
        company=instance.company, is_company_administrator=True
    )
    # force user to reconnect
    force_logout_user(user)

    # Operator Administrator permission
    if some_company_is_administrator.exists():
        set_operator_admin_permissions(user)
    elif user_in_group(user, "IncidentUser") and not instance.approved:
        set_incident_user_permissions(user)
    else:
        set_operator_user_permissions(user)


# Update incidents from IncidentUser
@receiver(pre_save, sender=CompanyUser)
def update_user_incidents(sender, instance, **kwargs):
    user = instance.user
    company = instance.company
    if (
        user
        and instance.approved
        and user_in_group(user, "IncidentUser")
        and company
        and company.identifier
        and not user.companyuser_set.exclude(pk=instance.pk)
        .exclude(approved=False)
        .exists()
    ):
        current_year = date.today().year
        incidents = user.incident_set.filter(
            company__isnull=True, regulator__isnull=True
        )
        incidents_per_company = (
            company.incident_set.exclude(contact_user=user)
            .filter(incident_notification_date__year=current_year)
            .count()
        )
        for incident in incidents:
            sector_for_ref = ""
            subsector_for_ref = ""
            sector = incident.affected_sectors.first()
            if sector:
                subsector_for_ref = sector.acronym[:3]
                if sector.parent:
                    sector_for_ref = sector.parent.acronym[:3]

            incidents_per_company += 1
            number_of_incident = f"{incidents_per_company:04}"

            incident.incident_id = f"{company.identifier}_{sector_for_ref}_{subsector_for_ref}_{number_of_incident}_{current_year}"
            incident.company = company
            incident.company_name = company.identifier
            incident.save()


@receiver(post_save, sender=RegulatorUser)
def update_regulator_user_groups(sender, instance, created, **kwargs):
    user = instance.user
    user.is_staff = False
    user.is_superuser = False

    force_logout_user(user)

    # Regulator Administrator permissions
    if instance.is_regulator_administrator:
        set_regulator_admin_permissions(user)
        return
    else:
        set_regulator_staff_permissions(user)
        return


@receiver(post_save, sender=ObserverUser)
def update_observer_user_groups(sender, instance, created, **kwargs):
    user = instance.user
    user.is_staff = False
    user.is_superuser = False

    force_logout_user(user)

    # Regulator Administrator permissions
    if instance.is_observer_administrator:
        set_observer_admin_permissions(user)
        return
    else:
        set_observer_user_permissions(user)
        return


# mark use for deletion to avoid removing group on inexisting object
@receiver(pre_delete, sender=User)
def mark_user_for_deletion(sender, instance, **kwargs):
    print("mark user for deletion")
    if not hasattr(_thread_locals, "deleting_users"):
        _thread_locals.deleting_users = set()
    _thread_locals.deleting_users.add(instance.pk)


# check if a user is being deleted
def is_user_being_deleted(user):
    return user.pk in getattr(_thread_locals, "deleting_users", set())


@receiver(post_delete, sender=CompanyUser)
@receiver(post_delete, sender=RegulatorUser)
@receiver(post_delete, sender=ObserverUser)
def delete_user_groups(sender, instance, **kwargs):
    user = instance.user

    if not is_user_being_deleted(user):
        group_names = [
            "PlatformAdmin",
            "RegulatorAdmin",
            "RegulatorUser",
            "OperatorAdmin",
            "OperatorUser",
            "IncidentUser",
            "ObserverAdmin",
            "ObserverUser",
        ]

        for group_name in group_names:
            try:
                group = Group.objects.get(name=group_name)
            except ObjectDoesNotExist:
                group = None

            if group and user.groups.filter(name=group_name).exists():
                # remove roles only if there is no linked company/regulator
                if (
                    group_name == "OperatorAdmin"
                    and not user.companyuser_set.filter(
                        is_company_administrator=True
                    ).exists()
                ):
                    user.groups.remove(group)
                    new_group, created = Group.objects.get_or_create(
                        name="OperatorUser"
                    )
                    if new_group:
                        user.groups.add(new_group)

                if group_name == "RegulatorAdmin" and user.regulators.count() < 1:
                    user.groups.remove(group)
                    new_group, created = Group.objects.get_or_create(
                        name="RegulatorUser"
                    )
                    if new_group:
                        user.groups.add(new_group)

        if not user.companyuser_set.exists():
            user.is_staff = False
            user.is_superuser = False
            new_group, created = Group.objects.get_or_create(name="IncidentUser")
            if new_group:
                user.groups.clear()
                user.groups.add(new_group)

            # Clear contact_user for incidents
            user.incident_set.filter(company__isnull=False).update(contact_user=None)
        else:
            user_companies = user.companyuser_set.values_list("company_id", flat=True)
            user.incident_set.filter(company__isnull=False).exclude(
                company__in=user_companies
            ).update(contact_user=None)

        user.save()

        force_logout_user(user)


def force_logout_user(user):
    # get the active sessions
    sessions = Session.objects.filter(expire_date__gte=now())
    for session in sessions:
        data = session.get_decoded()
        if data.get("_auth_user_id") == str(user.id):
            session.delete()

from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import Group
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from governanceplatform.models import User

from .helpers import user_in_group
from .models import CompanyUser, ObserverUser, PasswordUserHistory, RegulatorUser
from .permissions import (
    set_observer_admin_permissions,
    set_observer_user_permissions,
    set_operator_admin_permissions,
    set_operator_user_permissions,
    set_regulator_admin_permissions,
    set_regulator_staff_permissions,
)


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
        LogEntry.objects.log_action(
            user_id=user.id,
            content_type_id=ContentType.objects.get_for_model(User).pk,
            object_id=user.id,
            object_repr=user.email,
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
        LogEntry.objects.log_action(
            user_id=user.id,
            content_type_id=ContentType.objects.get_for_model(User).pk,
            object_id=user.id,
            object_repr=user.email,
            action_flag=6,
        )


user_logged_out.connect(log_user_logout)


@receiver(post_save, sender=CompanyUser)
def update_user_groups(sender, instance, created, **kwargs):
    user = instance.user
    user.is_staff = False
    user.is_superuser = False

    some_company_is_administrator = user.companyuser_set.filter(
        is_company_administrator=True
    )

    # Operator Administrator permission
    if some_company_is_administrator.exists():
        set_operator_admin_permissions(user)
    else:
        set_operator_user_permissions(user)
        return


# Update incidents from IncidentUser
@receiver(pre_save, sender=CompanyUser)
def update_user_incidents(sender, instance, **kwargs):
    user = instance.user
    if not user.companyuser_set.exists():
        user.incident_set.filter(company__isnull=True).update(
            company=instance.company, company_name=instance.company.identifier
        )


@receiver(post_save, sender=RegulatorUser)
def update_regulator_user_groups(sender, instance, created, **kwargs):
    user = instance.user
    user.is_staff = False
    user.is_superuser = False

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

    # Regulator Administrator permissions
    if instance.is_observer_administrator:
        set_observer_admin_permissions(user)
        return
    else:
        set_observer_user_permissions(user)
        return


@receiver(post_delete, sender=CompanyUser)
@receiver(post_delete, sender=RegulatorUser)
@receiver(post_delete, sender=ObserverUser)
def delete_user_groups(sender, instance, **kwargs):
    user = instance.user
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
            if group_name == "OperatorAdmin" and user.companies.count() < 1:
                user.groups.remove(group)
                new_group, created = Group.objects.get_or_create(name="OperatorUser")
                if new_group:
                    user.groups.add(new_group)

                user.is_active = False

            if group_name == "RegulatorAdmin" and user.regulators.count() < 1:
                user.groups.remove(group)
                new_group, created = Group.objects.get_or_create(name="RegulatorUser")
                if new_group:
                    user.groups.add(new_group)
                user.is_active = False

    if not user.companyuser_set.exists():
        user.is_staff = False
        user.is_superuser = False

    user.save()

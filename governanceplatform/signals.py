from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import ObserverUser, RegulatorUser, SectorCompanyContact
from .permissions import (
    set_observer_admin_permissions,
    set_observer_user_permissions,
    set_operator_admin_permissions,
    set_operator_user_permissions,
    set_regulator_admin_permissions,
    set_regulator_staff_permissions,
)


@receiver(post_save, sender=SectorCompanyContact)
def update_user_groups(sender, instance, created, **kwargs):
    user = instance.user
    user.is_staff = False
    user.is_superuser = False

    some_company_is_administrator = user.sectorcompanycontact_set.filter(
        is_company_administrator=True
    )

    # Operator Administrator permission
    if some_company_is_administrator.exists():
        set_operator_admin_permissions(user)
    else:
        set_operator_user_permissions(user)
        return


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


@receiver(post_delete, sender=SectorCompanyContact)
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
            # remove roles only if there is no linked company
            if group_name == "OperatorUser" and user.companies.count() < 1:
                user.groups.remove(group)
            if group_name == "OperatorAdmin" and user.companies.count() < 1:
                user.groups.remove(group)

    if not user.sectorcompanycontact_set.exists():
        user.is_staff = False
        user.is_superuser = False

    user.save()

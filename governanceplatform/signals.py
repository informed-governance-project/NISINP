from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import CompanyUser, RegulatorUser
from .permissions import (
    set_operator_admin_permissions,
    set_operator_user_permissions,
    set_regulator_admin_permissions,
    set_regulator_staff_permissions,
)


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


@receiver(post_delete, sender=CompanyUser)
@receiver(post_delete, sender=RegulatorUser)
def delete_user_groups(sender, instance, **kwargs):
    user = instance.user
    group_names = [
        "PlatformAdmin",
        "RegulatorAdmin",
        "RegulatorUser",
        "OperatorAdmin",
        "OperatorUser",
    ]

    for group_name in group_names:
        try:
            group = Group.objects.get(name=group_name)
        except ObjectDoesNotExist:
            group = None

        if group and user.groups.filter(name=group_name).exists():
            user.groups.remove(group)

    if not user.companyuser_set.exists():
        user.is_staff = False
        user.is_superuser = False

    user.save()

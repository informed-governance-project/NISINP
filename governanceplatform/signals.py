from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import CompanyAdministrator
from .permissions import (
    set_operator_admin_permissions,
    set_regulator_admin_permissions,
    set_regulator_staff_permissions,
)


@receiver(post_save, sender=CompanyAdministrator)
def update_user_groups(sender, instance, created, **kwargs):
    user = instance.user
    user.is_staff = False
    user.is_superuser = False

    some_company_is_regulator = user.companyadministrator_set.filter(
        company__is_regulator=True
    )
    some_company_is_administrator = user.companyadministrator_set.filter(
        is_company_administrator=True
    )

    # Platform Administrator permission
    # They are defined in the managers.py file

    # Regulator Administrator permissions
    if (
        some_company_is_regulator.exists()
        and some_company_is_regulator.filter(is_company_administrator=True).exists()
    ):
        set_regulator_admin_permissions(user)
        return

    # Regulator Staff permission
    if (
        some_company_is_regulator.exists()
        and some_company_is_regulator.filter(is_company_administrator=False).exists()
    ):
        set_regulator_staff_permissions(user)
        return

    # Operator Administrator permission
    if (
        some_company_is_administrator.exists()
        and some_company_is_administrator.filter(company__is_regulator=False).exists()
    ):
        set_operator_admin_permissions(user)
        return

    user.groups.clear()
    user.save()


@receiver(post_delete, sender=CompanyAdministrator)
def delete_user_groups(sender, instance, **kwargs):
    user = instance.user
    group_names = ["PlatformAdmin", "RegulatorAdmin", "RegulatorStaff", "OperatorAdmin"]

    for group_name in group_names:
        try:
            group = Group.objects.get(name=group_name)
        except ObjectDoesNotExist:
            group = None

        if group and user.groups.filter(name=group_name).exists():
            user.groups.remove(group)

    if not user.companyadministrator_set.exists():
        user.is_staff = False
        user.is_superuser = False

    user.save()

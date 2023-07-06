from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import CompanyAdministrator


@receiver(post_save, sender=CompanyAdministrator)
def update_user_groups(sender, instance, created, **kwargs):
    user = instance.user
    user.is_staff = False
    user.is_superuser = False

    group_permissions = {}
    some_company_is_regulator = user.companyadministrator_set.filter(
        company__is_regulator=True
    )
    some_company_is_administrator = user.companyadministrator_set.filter(
        is_company_administrator=True
    )

    # Platform Administrator permission
    # They are defined in the managers.py file

    # Operator Administrator permission
    if (
        some_company_is_administrator.exists()
        and some_company_is_administrator.filter(company__is_regulator=False).exists()
    ):
        user.is_staff = True
        group_permissions["OperatorAdmin"] = get_operator_admin_permissions()

    # Regulator Administrator permissions
    if (
        some_company_is_regulator.exists()
        and some_company_is_regulator.filter(is_company_administrator=True).exists()
    ):
        user.is_staff = True
        user.is_superuser = True
        group_permissions[
            "RegulatorAdmin"
        ] = []  # No permissions because is_superuser is True

    # Regulator Staff permission
    if (
        some_company_is_regulator.exists()
        and some_company_is_regulator.filter(is_company_administrator=False).exists()
    ):
        user.is_staff = True
        group_permissions["RegulatorStaff"] = get_regulator_staff_permissions()

    if not group_permissions or user.groups.exists():
        user.groups.clear()

    # Create or retrieve the groups and assign permissions
    for group_name, permissions in group_permissions.items():
        group, created = Group.objects.get_or_create(name=group_name)

        # Remove existing permissions not in the desired permissions list
        existing_permissions = group.permissions.all()
        permissions_to_remove = existing_permissions.exclude(codename__in=permissions)
        group.permissions.remove(*permissions_to_remove)

        # Add the desired permissions not already assigned to the group
        permissions_to_assign = Permission.objects.filter(codename__in=permissions)
        group.permissions.add(*permissions_to_assign)

        # Add the user to the group
        user.groups.add(group)

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


def get_operator_admin_permissions():
    group_permissions = []
    models = {
        "user": ["add", "change", "delete"],
        "sectorcontact": ["add", "change", "delete"],
        "companyadministrator": ["add", "change", "delete"],
        "company": ["change"],
    }

    for model, permissions in models.items():
        for permission in permissions:
            group_permissions.append(permission + "_" + model)

    return group_permissions


def get_regulator_staff_permissions():
    group_permissions = []
    models = {
        "user": ["add", "change", "delete"],
        "sectorcontact": ["add", "change", "delete"],
        "companyadministrator": ["add", "change", "delete"],
        "company": ["change"],
    }

    for model, permissions in models.items():
        for permission in permissions:
            group_permissions.append(permission + "_" + model)

    return group_permissions

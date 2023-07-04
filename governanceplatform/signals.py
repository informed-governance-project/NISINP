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

    # Define a dictionary of group names and the associated permissions

    if (
        some_company_is_administrator.exists()
        and some_company_is_administrator.filter(company__is_regulator=False).exists()
    ):
        user.is_staff = True
        group_permissions["OperatorAdmin"] = get_operator_admin_permissions()

    if (
        some_company_is_regulator.exists()
        and some_company_is_regulator.filter(is_company_administrator=True).exists()
    ):
        # Regulator Administrator permissions
        user.is_staff = True
        user.is_superuser = True

    if (
        some_company_is_regulator.exists()
        and some_company_is_regulator.filter(is_company_administrator=False).exists()
    ):
        # Regulator Staff permission
        user.is_staff = True
        group_permissions["RegulatorStaff"] = get_regulator_staff_permissions()

    if not group_permissions or user.groups.exists():
        user.groups.clear()

    # Create or retrieve the groups and assign permissions

    for group_name, permissions in group_permissions.items():
        group, created = Group.objects.get_or_create(name=group_name)
        if created:
            for permission in permissions:
                app_label, codename = permission.split(".", 1)
                group.permissions.add(
                    Permission.objects.get(
                        content_type__app_label=app_label, codename=codename
                    )
                )
        # Add the user to the group
        user.groups.add(group)

    user.save()


@receiver(post_delete, sender=CompanyAdministrator)
def delete_user_groups(sender, instance, **kwargs):
    user = instance.user
    group_names = ["OperatorAdmin", "RegulatorStaff"]

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
    operator_admin_permissions = []
    model_permissions = ["add", "change", "delete"]
    models = ["user"]

    for model in models:
        for permission in model_permissions:
            operator_admin_permissions.append(
                "governanceplatform" + "." + permission + "_" + model
            )

    return operator_admin_permissions


def get_regulator_staff_permissions():
    operator_admin_permissions = []
    model_permissions = ["add", "change", "delete"]
    models = ["user", "sector"]

    for model in models:
        for permission in model_permissions:
            operator_admin_permissions.append(
                "governanceplatform" + "." + permission + "_" + model
            )

    return operator_admin_permissions

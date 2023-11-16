from django.contrib.auth.models import Group, Permission


def set_permissions_for_user(user, is_superuser, is_staff, group_name, permissions):
    group_permissions = permission_formatting(permissions)
    group = add_group_permissions(group_name, group_permissions)

    add_user_group(user, is_superuser, is_staff, group)


def add_user_group(user, is_superuser=False, is_staff=False, group=None):
    user.is_staff = is_staff
    user.is_superuser = is_superuser
    if not group or user.groups.exists():
        user.groups.clear()
    if group:
        user.groups.add(group)
    user.save()


def permission_formatting(permissions):
    group_permissions = []
    for model, list_permissions in permissions.items():
        for permission in list_permissions:
            group_permissions.append(f"{permission}_{model}")
    return group_permissions


def add_group_permissions(group_name, group_permissions):
    group, created = Group.objects.get_or_create(name=group_name)

    # Remove existing permissions not in the desired permissions list
    existing_permissions = group.permissions.all()
    permissions_to_remove = existing_permissions.exclude(codename__in=group_permissions)
    group.permissions.remove(*permissions_to_remove)

    # Add the desired permissions not already assigned to the group
    permissions_to_assign = Permission.objects.filter(codename__in=group_permissions)
    group.permissions.add(*permissions_to_assign)

    return group


def set_platform_admin_permissions(user):
    set_permissions_for_user(
        user,
        is_superuser=False,
        is_staff=True,
        group_name="PlatformAdmin",
        permissions={
            "user": ["add", "change", "delete"],
            "regulatoruser": ["add", "change", "delete"],
            "regulator": ["add", "change", "delete"],
            "regulation": ["add", "change", "delete"],
        },
    )


def set_regulator_admin_permissions(user):
    set_permissions_for_user(
        user,
        is_superuser=True,
        is_staff=True,
        group_name="RegulatorAdmin",
        permissions={},
    )


def set_regulator_staff_permissions(user):
    set_permissions_for_user(
        user,
        is_superuser=False,
        is_staff=True,
        group_name="RegulatorUser",
        permissions={
            "user": ["add", "view", "import", "export"],
            "sectorcontact": ["add", "view"],
            "companyuser": ["add", "change"],
            "company": ["add", "view"],
            "sector": ["change"],
        },
    )


def set_operator_admin_permissions(user):
    set_permissions_for_user(
        user,
        is_superuser=False,
        is_staff=True,
        group_name="OperatorAdmin",
        permissions={
            "user": ["add", "change", "delete"],
            "sectorcontact": ["add", "change", "delete"],
            "companyuser": ["add", "change", "delete"],
            "company": ["change"],
        },
    )


def set_operator_user_permissions(user):
    user.is_staff = False
    set_permissions_for_user(
        user,
        is_superuser=False,
        is_staff=False,
        group_name="OperatorUser",
        permissions={},
    )

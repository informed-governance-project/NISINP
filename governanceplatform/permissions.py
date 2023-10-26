from django.contrib.auth.models import Group, Permission


def set_permissions_for_user(user, is_superuser, group_name, permissions):
    group_permissions = permission_formatting(permissions)
    group = add_group_permissions(group_name, group_permissions)

    add_user_group(user, is_superuser, group)


def add_user_group(user, is_superuser=False, group=None):
    user.is_staff = True
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
        group_name="PlatformAdmin",
        permissions={
            "user": ["add", "change", "delete"],
            "regulator": ["add", "change", "delete"],
        },
    )


def set_regulator_admin_permissions(user):
    set_permissions_for_user(
        user,
        is_superuser=True,
        group_name="RegulatorAdmin",
        permissions={},
    )


def set_regulator_staff_permissions(user):
    set_permissions_for_user(
        user,
        is_superuser=False,
        group_name="RegulatorStaff",
        permissions={
            "user": ["add", "change", "delete", "import", "export"],
            "sectorcontact": ["add", "change", "delete"],
            "companyadministrator": ["add", "change", "delete"],
            "company": ["change"],
        },
    )


def set_operator_admin_permissions(user):
    set_permissions_for_user(
        user,
        is_superuser=False,
        group_name="OperatorAdmin",
        permissions={
            "user": ["add", "change", "delete"],
            "sectorcontact": ["add", "change", "delete"],
            "companyadministrator": ["add", "change", "delete"],
            "company": ["change"],
        },
    )

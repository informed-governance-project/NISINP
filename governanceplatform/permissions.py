from django.contrib.auth.models import Group, Permission


def set_regulator_admin_permissions(user):
    is_staff = True
    is_superuser = True
    group_name = "RegulatorAdmin"

    add_user_group(
        user,
        is_staff,
        is_superuser,
        Group.objects.get_or_create(name=group_name)[0],
    )


def set_operator_admin_permissions(user):
    is_staff = True
    is_superuser = False
    group_name = "OperatorAdmin"
    models = {
        "user": ["add", "change", "delete"],
        "sectorcontact": ["add", "change", "delete"],
        "companyadministrator": ["add", "change", "delete"],
        "company": ["change"],
    }
    group_permissions = permission_formatting(models)

    add_user_group(
        user,
        is_staff,
        is_superuser,
        add_group_permissions(group_name, group_permissions),
    )


def set_regulator_staff_permissions(user):
    is_staff = True
    is_superuser = False
    group_name = "RegulatorStaff"
    models = {
        "user": ["add", "change", "delete", "import", "export"],
        "sectorcontact": ["add", "change", "delete"],
        "companyadministrator": ["add", "change", "delete"],
        "company": ["change"],
    }
    group_permissions = permission_formatting(models)

    add_user_group(
        user,
        is_staff,
        is_superuser,
        add_group_permissions(group_name, group_permissions),
    )


def set_platform_admin_permissions(user):
    is_staff = True
    is_superuser = False
    group_name = "PlatformAdmin"
    models = {
        "user": ["add", "change", "delete"],
        "companyadministrator": ["add", "change", "delete"],
        "company": ["add", "change", "delete"],
    }
    group_permissions = permission_formatting(models)

    add_user_group(
        user,
        is_staff,
        is_superuser,
        add_group_permissions(group_name, group_permissions),
    )


def add_user_group(user, is_staff=False, is_superuser=False, group=None):
    user.is_staff = is_staff
    user.is_superuser = is_superuser
    if not group or user.groups.exists():
        user.groups.clear()
    if group:
        user.groups.add(group)
    user.save()


def permission_formatting(models):
    group_permissions = []
    for model, permissions in models.items():
        for permission in permissions:
            group_permissions.append(permission + "_" + model)
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

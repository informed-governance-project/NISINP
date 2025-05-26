from django.contrib.auth.models import Group, Permission

GROUP_PERMISSIONS = {
    "PlatformAdmin": {
        "site": ["change"],
        "user": ["add", "change", "delete"],
        "regulatoruser": ["add", "change", "delete"],
        "regulator": ["add", "change", "delete"],
        "regulation": ["add", "change", "delete"],
        "observeruser": ["add", "change", "delete"],
        "observer": ["add", "change", "delete"],
        "observerregulation": ["add", "change", "delete"],
        "entitycategory": ["add", "change", "delete"],
    },
    "RegulatorAdmin": {},
    "RegulatorUser": {
        "user": ["add", "view", "import", "export"],
        "companyuser": ["add", "view", "change", "delete"],
        "company": ["add", "view", "change", "delete"],
        "sector": ["change"],
        "observationrecommendation": ["add", "view", "change", "delete"],
    },
    "ObserverAdmin": {
        "user": ["add", "change", "delete"],
        "observeruser": ["add", "change", "delete"],
        "observer": ["change"],
    },
    "ObserverUser": {},
    "OperatorAdmin": {
        "user": ["add", "change"],
        "companyuser": ["view", "change", "delete"],
        "company": ["change"],
    },
    "OperatorUser": {},
    "IncidentUser": {},
}


def set_permissions_for_user(user, is_superuser, is_staff, group_name, permissions):
    group = update_group_permissions(group_name, permissions)
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


def update_group_permissions(group_name, permissions):
    group_permissions = permission_formatting(permissions)
    group = add_group_permissions(group_name, group_permissions)
    return group


def update_all_group_permissions():
    for group_name, permissions in GROUP_PERMISSIONS.items():
        update_group_permissions(group_name, permissions)


def set_platform_admin_permissions(user):
    set_permissions_for_user(
        user,
        is_superuser=False,
        is_staff=True,
        group_name="PlatformAdmin",
        permissions=GROUP_PERMISSIONS["PlatformAdmin"],
    )


def set_regulator_admin_permissions(user):
    set_permissions_for_user(
        user,
        is_superuser=True,
        is_staff=True,
        group_name="RegulatorAdmin",
        permissions=GROUP_PERMISSIONS["RegulatorAdmin"],
    )


def set_observer_admin_permissions(user):
    set_permissions_for_user(
        user,
        is_superuser=False,
        is_staff=True,
        group_name="ObserverAdmin",
        permissions=GROUP_PERMISSIONS["ObserverAdmin"],
    )


def set_observer_user_permissions(user):
    user.is_staff = False
    set_permissions_for_user(
        user,
        is_superuser=False,
        is_staff=False,
        group_name="ObserverUser",
        permissions=GROUP_PERMISSIONS["ObserverUser"],
    )


def set_regulator_staff_permissions(user):
    set_permissions_for_user(
        user,
        is_superuser=False,
        is_staff=True,
        group_name="RegulatorUser",
        permissions=GROUP_PERMISSIONS["RegulatorUser"],
    )


def set_operator_admin_permissions(user):
    set_permissions_for_user(
        user,
        is_superuser=False,
        is_staff=True,
        group_name="OperatorAdmin",
        permissions=GROUP_PERMISSIONS["OperatorAdmin"],
    )


def set_operator_user_permissions(user):
    user.is_staff = False
    set_permissions_for_user(
        user,
        is_superuser=False,
        is_staff=False,
        group_name="OperatorUser",
        permissions=GROUP_PERMISSIONS["OperatorUser"],
    )


def set_incident_user_permissions(user):
    user.is_staff = False
    set_permissions_for_user(
        user,
        is_superuser=False,
        is_staff=False,
        group_name="IncidentUser",
        permissions=GROUP_PERMISSIONS["IncidentUser"],
    )

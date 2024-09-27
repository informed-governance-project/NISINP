from django.db import migrations


def create_new_permissions(apps, schema_editor):
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    new_permissions = {
        "observerregulation": ["add", "change", "delete", "view"],
        "entitycategory": ["add", "change", "delete", "view"],
    }

    for model, perms in new_permissions.items():
        try:
            content_type = ContentType.objects.create(
                app_label="governanceplatform", model=model
            )
        except ContentType.DoesNotExist:
            continue

        for perm in perms:
            codename = f"{perm}_{model}"
            name = f"Can {perm} {model}"
            Permission.objects.create(
                codename=codename, content_type=content_type, name=name
            )


def update_permissions(apps, schema_editor):
    def permission_formatting(permissions):
        group_permissions = []
        for model, list_permissions in permissions.items():
            for permission in list_permissions:
                group_permissions.append(f"{permission}_{model}")
        return group_permissions

    def add_group_permissions(group_name, group_permissions):
        try:
            group = Group.objects.get(name=group_name)

            permissions_to_assign = Permission.objects.filter(
                codename__in=group_permissions
            )
            for permission in permissions_to_assign:
                group.permissions.add(permission)
            group.save()
        except Group.DoesNotExist:
            pass

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    groups_permissions = {
        "PlatformAdmin": {
            "observerregulation": ["add", "change", "delete"],
            "entitycategory": ["add", "change", "delete"],
        },
    }
    for group_name, permissions in groups_permissions.items():
        group_permissions = permission_formatting(permissions)
        add_group_permissions(group_name, group_permissions)


class Migration(migrations.Migration):
    dependencies = [
        ("governanceplatform", "0025_entitycategory_entitycategorytranslation_and_more"),
    ]

    operations = [
        migrations.RunPython(create_new_permissions),
        migrations.RunPython(update_permissions),
    ]

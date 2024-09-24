from django.db import migrations


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
            existing_permissions = group.permissions.all()
            permissions_to_remove = existing_permissions.exclude(
                codename__in=group_permissions
            )
            group.permissions.remove(*permissions_to_remove)

            permissions_to_assign = Permission.objects.filter(
                codename__in=group_permissions
            )
            group.permissions.add(*permissions_to_assign)
            group.save()
        except Group.DoesNotExist:
            pass

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    groups_permissions = {
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
    }

    for group_name, permissions in groups_permissions.items():
        group_permissions = permission_formatting(permissions)
        add_group_permissions(group_name, group_permissions)


class Migration(migrations.Migration):
    dependencies = [
        ("governanceplatform", "0025_entitycategory_entitycategorytranslation_and_more"),
    ]

    operations = [
        migrations.RunPython(update_permissions),
    ]

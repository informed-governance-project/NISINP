# Generated by Django 5.0.7 on 2024-07-23 14:59

from django.db import migrations


def create_new_permissions(apps, schema_editor):
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    new_permissions = {
        "observeruser": ["add", "change", "delete", "view"],
        "observer": ["add", "change", "delete", "view"],
    }

    for model, perms in new_permissions.items():
        try:
            content_type = ContentType.objects.get(
                app_label="governanceplatform", model=model
            )
        except ContentType.DoesNotExist:
            continue

        for perm in perms:
            codename = f"{perm}_{model}"
            name = f"Can {perm} {model}"
            Permission.objects.get_or_create(
                codename=codename, content_type=content_type, defaults={"name": name}
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

    def remove_old_permissions():
        old_permissions = {
            "cert": ["add", "change", "delete", "view"],
            "certuser": ["add", "change", "delete", "view"],
        }
        group_old_permissions = permission_formatting(old_permissions)
        Permission.objects.filter(codename__in=group_old_permissions).delete()

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
        },
        "ObserverAdmin": {
            "user": ["add", "change", "delete"],
            "observeruser": ["add", "change", "delete"],
            "observer": ["change"],
        },
    }

    for group_name, permissions in groups_permissions.items():
        group_permissions = permission_formatting(permissions)
        add_group_permissions(group_name, group_permissions)
        remove_old_permissions()


class Migration(migrations.Migration):
    dependencies = [
        ("governanceplatform", "0018_rename_cert_groups"),
    ]

    operations = [
        migrations.RunPython(create_new_permissions),
        migrations.RunPython(update_permissions),
    ]

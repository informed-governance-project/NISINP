from django.db import migrations

GROUP_PERMISSIONS = {
    "RegulatorAdmin": {
        # Administration
        "logentry": ["view"],
        "scriptlogentry": ["view"],
        # Governance
        "regulation": ["view"],
        "functionality": ["view"],
        "observer": ["view"],
        "entitycategory": ["view"],
        "regulatoruser": ["add", "change", "delete"],
        "regulator": ["view", "change"],
        "company": ["add", "change", "delete"],
        "companyuser": ["add", "change", "delete"],
        "sector": ["add", "change", "delete"],
        "user": ["add", "change", "delete"],
        # Incident
        "email": ["add", "change", "delete"],
        "impact": ["add", "change", "delete"],
        "workflow": ["add", "change", "delete"],
        "sectorregulation": ["add", "change", "delete"],
        "question": ["add", "change", "delete"],
        "questionoptions": ["add", "change", "delete"],
        "questioncategory": ["add", "change", "delete"],
        "questioncategoryoptions": ["add", "change", "delete"],
        "sectorregulationworkflowemail": ["add", "change", "delete"],
        "sectorregulationworkflow": ["add", "change", "delete"],
        # Reporting
        "companyreporting": ["add", "change", "delete"],
        "assetdata": ["add", "change", "delete"],
        "vulnerabilitydata": ["add", "change", "delete"],
        "threatdata": ["add", "change", "delete"],
        "servicestat": ["add", "change", "delete"],
        "riskdata": ["add", "change", "delete"],
        "recommendationdata": ["add", "change", "delete"],
        "sectorreportconfiguration": ["add", "change", "delete"],
        "observationrecommendation": ["add", "change", "delete"],
        "observation": ["add", "change", "delete"],
        "observationrecommendationthrough": ["add", "change", "delete"],
        "logreporting": ["add", "change", "delete"],
        "configuration": ["add", "change", "delete"],
        "color": ["add", "change", "delete"],
        "template": ["add", "change", "delete"],
        "project": ["add", "change", "delete"],
        "companyproject": ["add", "change", "delete"],
        "generatedreport": ["add", "change", "delete"],
        # Security Objectives
        "maturitylevel": ["add", "change", "delete"],
        "domain": ["add", "change", "delete"],
        "securityobjective": ["add", "change", "delete"],
        "securityobjectiveemail": ["add", "change", "delete"],
        "standard": ["add", "change", "delete"],
        "securityobjectivesinstandard": ["add", "change", "delete"],
        "securitymeasure": ["add", "change", "delete"],
        "standardanswergroup": ["add", "change", "delete"],
        "standardanswer": ["add", "change", "delete"],
        "securitymeasureanswer": ["add", "change", "delete"],
        "securityobjectivestatus": ["add", "change", "delete"],
        "logstandardanswer": ["add", "change", "delete"],
    },
}


def remove_superuser_flag(apps, schema_editor):
    User = apps.get_model("governanceplatform", "User")
    User.objects.filter(is_superuser=True).update(is_superuser=False)


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

    for group_name, permissions in GROUP_PERMISSIONS.items():
        group_permissions = permission_formatting(permissions)
        add_group_permissions(group_name, group_permissions)


class Migration(migrations.Migration):

    dependencies = [
        ("governanceplatform", "0057_company_sectors"),
    ]

    operations = [
        migrations.RunPython(remove_superuser_flag),
        migrations.RunPython(update_permissions),
    ]

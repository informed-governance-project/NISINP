# Generated by Django 5.1.2 on 2024-11-14 13:07

from django.db import migrations


def transfer_user(apps, schema_editor):
    SectorCompanyContact = apps.get_model("governanceplatform", "SectorCompanyContact")
    CompanyUser = apps.get_model("governanceplatform", "CompanyUser")

    for ssc in SectorCompanyContact.objects.all():
        user = None
        user, created = CompanyUser.objects.get_or_create(
            company=ssc.company,
            user=ssc.user,
        )
        if created:
            user = CompanyUser.objects.get(
                company=ssc.company,
                user=ssc.user,
            )
        if user is not None:
            user.sectors.add(ssc.sector)
            if ssc.is_company_administrator is True:
                user.is_company_administrator = 1
            user.save()


class Migration(migrations.Migration):

    dependencies = [
        ("governanceplatform", "0033_companyuser"),
    ]

    operations = [
        migrations.RunPython(transfer_user),
    ]

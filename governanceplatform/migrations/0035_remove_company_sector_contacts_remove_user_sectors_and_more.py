# Generated by Django 5.1.2 on 2024-11-15 06:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("governanceplatform", "0034_migrate_sector_contact"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="company",
            name="sector_contacts",
        ),
        migrations.RemoveField(
            model_name="user",
            name="sectors",
        ),
        migrations.AlterField(
            model_name="user",
            name="companies",
            field=models.ManyToManyField(
                through="governanceplatform.CompanyUser",
                to="governanceplatform.company",
                verbose_name="Companies",
            ),
        ),
        migrations.DeleteModel(
            name="SectorCompanyContact",
        ),
    ]

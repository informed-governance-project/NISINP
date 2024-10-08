# Generated by Django 5.1.1 on 2024-09-25 09:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("governanceplatform", "0026_update_permissions"),
    ]

    operations = [
        migrations.AddField(
            model_name="company",
            name="entity_categories",
            field=models.ManyToManyField(
                to="governanceplatform.entitycategory", verbose_name="Entity categories"
            ),
        ),
        migrations.AlterField(
            model_name="observerregulation",
            name="incident_rule",
            field=models.JSONField(
                blank=True, default=dict, null=True, verbose_name="Incident rules"
            ),
        ),
    ]

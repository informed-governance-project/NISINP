# Generated by Django 5.1 on 2024-09-09 09:30

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("incidents", "0011_alter_email_name_alter_emailtranslation_subject"),
    ]

    operations = [
        migrations.AlterField(
            model_name="workflowtranslation",
            name="name",
            field=models.CharField(
                default="[MISSING_TRANSLATION]", max_length=255, verbose_name="Name"
            ),
            preserve_default=False,
        ),
    ]

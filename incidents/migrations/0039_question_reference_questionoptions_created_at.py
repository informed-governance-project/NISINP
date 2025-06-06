# Generated by Django 5.2.1 on 2025-06-02 11:36

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("incidents", "0038_questionoptionshistory_category_option"),
    ]

    operations = [
        migrations.AddField(
            model_name="question",
            name="reference",
            field=models.CharField(
                blank=True,
                default=None,
                max_length=255,
                null=True,
                verbose_name="Creator name",
            ),
        ),
        migrations.AddField(
            model_name="questionoptions",
            name="created_at",
            field=models.DateTimeField(
                default=django.utils.timezone.now, verbose_name="Created at"
            ),
        ),
    ]

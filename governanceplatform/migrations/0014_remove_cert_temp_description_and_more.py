# Generated by Django 5.0.7 on 2024-07-23 13:24

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("governanceplatform", "0013_auto_20240723_1521"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="cert",
            name="temp_description",
        ),
        migrations.RemoveField(
            model_name="cert",
            name="temp_full_name",
        ),
        migrations.RemoveField(
            model_name="cert",
            name="temp_name",
        ),
    ]

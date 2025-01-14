# Generated by Django 5.1.4 on 2025-01-14 11:55

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("securityobjectives", "0002_securityobjectivesinstandard_priority"),
    ]

    operations = [
        migrations.AlterField(
            model_name="standardanswer",
            name="status",
            field=models.CharField(
                choices=[
                    ("UNDE", "Unsubmitted"),
                    ("DELIV", "Under review"),
                    ("PASS", "Passed"),
                    ("FAIL", "Failed"),
                    ("OUT", "Submission overdue"),
                ],
                default="UNDE",
                max_length=5,
                verbose_name="Status",
            ),
        ),
    ]

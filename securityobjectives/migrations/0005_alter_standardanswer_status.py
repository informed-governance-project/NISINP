# Generated by Django 5.1.7 on 2025-04-02 08:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "securityobjectives",
            "0004_remove_securityobjective_unique_unique_code_and_more",
        ),
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
                    ("PASSM", "Passed and sent"),
                    ("FAIL", "Failed"),
                    ("FAILM", "Failed and sent"),
                    ("OUT", "Submission overdue"),
                ],
                default="UNDE",
                max_length=5,
                verbose_name="Status",
            ),
        ),
    ]

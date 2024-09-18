# Generated by Django 5.0.8 on 2024-09-17 08:16

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("incidents", "0016_migrate_existing_data"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="question",
            options={"verbose_name": "Question", "verbose_name_plural": "Questions"},
        ),
        migrations.AlterModelOptions(
            name="questiontranslation",
            options={
                "default_permissions": (),
                "managed": True,
                "verbose_name": "Question Translation",
            },
        ),
        migrations.RemoveField(
            model_name="answer",
            name="predefined_answers",
        ),
        migrations.RemoveField(
            model_name="answer",
            name="question",
        ),
        migrations.RemoveField(
            model_name="predefinedanswer",
            name="position",
        ),
        migrations.RemoveField(
            model_name="predefinedanswer",
            name="question",
        ),
        migrations.RemoveField(
            model_name="question",
            name="category",
        ),
        migrations.RemoveField(
            model_name="question",
            name="is_mandatory",
        ),
        migrations.RemoveField(
            model_name="question",
            name="position",
        ),
        migrations.RemoveField(
            model_name="questioncategory",
            name="position",
        ),
    ]
# Generated by Django 5.1.2 on 2024-10-18 09:28

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("incidents", "0025_populate_question_category_option"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="questionoptions",
            name="category",
        ),
    ]
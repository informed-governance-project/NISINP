# Generated by Django 5.1.1 on 2024-10-10 09:31

from django.db import migrations


def transfer_predefined_answer_options(apps, schema_editor):
    Answer = apps.get_model("incidents", "Answer")
    PredefinedAnswer = apps.get_model("incidents", "PredefinedAnswer")

    for answer in Answer.objects.all():
        predefined_answer_options = answer.predefined_answer_options.all()
        predefined_answers = PredefinedAnswer.objects.filter(
            id__in=[pao.predefined_answer_id for pao in predefined_answer_options]
        )

        answer.predefined_answers.set(predefined_answers)
        answer.save()


class Migration(migrations.Migration):
    dependencies = [
        ("incidents", "0021_answer_predefined_answers"),
    ]

    operations = [
        migrations.RunPython(transfer_predefined_answer_options),
    ]

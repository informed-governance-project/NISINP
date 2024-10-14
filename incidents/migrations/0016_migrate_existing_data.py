from django.db import connection, migrations


def migrate_data(apps, schema_editor):
    # Get the models
    Workflow = apps.get_model("incidents", "Workflow")
    Question = apps.get_model("incidents", "Question")
    Answer = apps.get_model("incidents", "Answer")
    IncidentWorkflow = apps.get_model("incidents", "IncidentWorkflow")
    QuestionOptions = apps.get_model("incidents", "QuestionOptions")
    PredefinedAnswer = apps.get_model("incidents", "PredefinedAnswer")
    PredefinedAnswerOptions = apps.get_model("incidents", "PredefinedAnswerOptions")
    QuestionCategory = apps.get_model("incidents", "QuestionCategory")
    QuestionCategoryOptions = apps.get_model("incidents", "QuestionCategoryOptions")
    workflow_questions_table = "incidents_workflow_questions"

    with connection.cursor() as cursor:
        # Query the M2M table directly
        cursor.execute(
            f"SELECT workflow_id, question_id FROM {workflow_questions_table}"
        )
        workflow_questions_pairs = cursor.fetchall()

    for workflow_id, question_id in workflow_questions_pairs:
        workflow = Workflow.objects.get(id=workflow_id)
        question = Question.objects.get(id=question_id)

        # Create QuestionOptions instance
        question_option = QuestionOptions.objects.create(
            report=workflow,
            question=question,
            is_mandatory=question.is_mandatory,
            position=question.position,
            category=question.category,
        )

        # Migrate PredefinedAnswer data to PredefinedAnswerOptions
        for predefined_answer in PredefinedAnswer.objects.filter(question=question):
            PredefinedAnswerOptions.objects.create(
                predefined_answer=predefined_answer,
                question_options=question_option,
                position=predefined_answer.position,
            )

    # Update existing Answer records to use the new fields
    for answer in Answer.objects.all():
        try:
            incident_workflow = IncidentWorkflow.objects.get(
                pk=answer.incident_workflow_id
            )
            question_option = QuestionOptions.objects.get(
                question=answer.question, report=incident_workflow.workflow
            )
            answer.question_options = question_option

            for predefined_answer in answer.predefined_answers.all():
                answer.predefined_answer_options.set(
                    PredefinedAnswerOptions.objects.filter(
                        question_options=question_option,
                        predefined_answer=predefined_answer,
                    )
                )
            answer.save()  # Save the instance after updating the field
        except (IncidentWorkflow.DoesNotExist, QuestionOptions.DoesNotExist):
            pass

    # Migrate QuestionCategory data to QuestionCategoryOptions
    for category in QuestionCategory.objects.all():
        QuestionCategoryOptions.objects.create(
            question_category=category, position=category.position
        )


class Migration(migrations.Migration):
    dependencies = [
        ("incidents", "0015_alter_sectorregulationworkflow_options_and_more"),
    ]

    operations = [
        migrations.RunPython(migrate_data),
    ]

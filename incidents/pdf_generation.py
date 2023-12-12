import os
from typing import Dict, List

from django.http import HttpRequest
from django.template.loader import render_to_string
from weasyprint import CSS, HTML

from .models import Answer, Incident


def get_pdf_report(incident: Incident, request: HttpRequest):
    sectors: Dict[str, List[str]] = {}

    for sector in incident.affected_sectors.all():
        if sector.name not in sectors:
            sectors[sector.name] = []
        sectors[sector.name].append(sector.name)

    final_questions_answers: Dict[str, str, List[str]] = {}
    for incident_workflow in incident.workflows.all():
        answers = Answer.objects.all().filter(
            incident_workflow=incident_workflow
        )
        for answer in answers.all():
            populate_questions_answers(
                answer,
                final_questions_answers,
            )
            print('answers')
    print(final_questions_answers)

    # Render the HTML file
    output_from_parsed_template = render_to_string(
        "report/template.html",
        {
            "incident": incident,
            "final_questions_answers": final_questions_answers,
            "regulation": incident.sector_regulation.regulation,
            "services": sectors,
        },
        request=request,
    )

    base_url = os.path.abspath("incidents/templates/report")
    htmldoc = HTML(string=output_from_parsed_template, base_url=base_url)

    stylesheets = [
        CSS(os.path.join(base_url, "css/custom.css")),
    ]

    return htmldoc.write_pdf(stylesheets=stylesheets)


def populate_questions_answers(answer: Answer, preliminary_questions_answers: Dict):
    category_label = answer.question.category.label
    if category_label not in preliminary_questions_answers:
        preliminary_questions_answers[category_label] = {}
    if answer.question.label not in preliminary_questions_answers[category_label]:
        preliminary_questions_answers[category_label][answer.question.label] = []
    for predefined_answer in answer.predefined_answers.all():
        preliminary_questions_answers[category_label][answer.question.label].append(
            predefined_answer.predefined_answer
        )
    if not preliminary_questions_answers[category_label][answer.question.label]:
        preliminary_questions_answers[category_label][answer.question.label].append(
            answer.answer
        )

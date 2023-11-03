import os
from typing import Dict, List

from django.http import HttpRequest
from django.template.loader import render_to_string
from weasyprint import CSS, HTML

from .models import Answer, Incident


def get_pdf_report(incident: Incident, request: HttpRequest):
    regulations = []
    services: Dict[str, List[str]] = {}
    for regulation in incident.regulations.all():
        regulations.append(regulation.label)
    for service in incident.affected_services.all():
        if service.sector.name not in services:
            services[service.sector.name] = []
        services[service.sector.name].append(service.name)

    preliminary_questions_answers: Dict[str, str, List[str]] = {}
    final_questions_answers: Dict[str, str, List[str]] = {}
    for answer in incident.answer_set.all():
        populate_questions_answers(
            answer,
            final_questions_answers,
            # preliminary_questions_answers
            # if answer.question.is_preliminary
            # else final_questions_answers,
        )

    # Render the HTML file
    output_from_parsed_template = render_to_string(
        "report/template.html",
        {
            "incident": incident,
            "preliminary_questions_answers": preliminary_questions_answers,
            "final_questions_answers": final_questions_answers,
            "regulations": regulations,
            "services": services,
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

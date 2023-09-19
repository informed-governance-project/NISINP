import os
from datetime import datetime
from typing import Dict
from typing import List
from weasyprint import CSS
from weasyprint import HTML

from django.conf import settings
from django.http import HttpRequest
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _

from .models import (
    Answer,
    Incident,
    PredifinedAnswer,
    Question,
    QuestionCategory,
)


def get_pdf_report(incident_id: int, request: HttpRequest):
    incident = Incident.objects.get(pk=incident_id)

    regulations = []
    services: Dict[str, List[str]] = {}
    for regulation in incident.regulations.all():
        regulations.append(regulation.label)
    for service in incident.affected_services.all():
        if service.sector.name not in services:
            services[service.sector.name] = []
        services[service.sector.name].append(service.name)

    questions_answers: Dict[str, List[str]] = {}
    for answer in incident.answer_set.all():
        if answer.question.label not in questions_answers:
            questions_answers[answer.question.label] = []
        questions_answers[answer.question.label].append(answer.answer)

    # Render the HTML file
    output_from_parsed_template = render_to_string(
        "report/template.html",
        {
            "incident": incident,
            "questions_answers": questions_answers,
            "regulations": regulations,
            "services": services,
        },
        request=request,
    )

    base_url = os.path.abspath("incidents/templates/report")
    htmldoc = HTML(string=output_from_parsed_template, base_url=base_url)

    stylesheets = [
        CSS(
            os.path.join(base_url, "css/custom.css")
        ),
    ]

    return htmldoc.write_pdf(stylesheets=stylesheets)



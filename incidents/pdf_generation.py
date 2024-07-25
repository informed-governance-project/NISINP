import os
from typing import Dict, List

from django.http import HttpRequest
from django.template.loader import render_to_string
from weasyprint import CSS, HTML

from governanceplatform.settings import BASE_DIR

from .models import Answer, Incident, IncidentWorkflow


def get_pdf_report(incident: Incident, incident_workflow: IncidentWorkflow, request: HttpRequest):
    # TO DO : improve for more than 2 level ?
    sectors: Dict[str, List[str]] = {}
    for sector in incident.affected_sectors.all():
        if sector.parent:
            if sector.parent.name not in sectors:
                sectors[sector.parent.name] = []
            sectors[sector.parent.name].append(sector.name)
        else:
            if sector.name not in sectors:
                sectors[sector.name] = []

    incident_workflows_answer: Dict[str, Dict[str, str, List[str]]] = {}
    incident_workflows_impact: Dict[str, List[str]] = {}
    # display for the full incident or just a report
    if incident_workflow is None:
        report_list = incident.get_latest_incident_workflows()
    else:
        report_list = [incident_workflow]

    for incident_workflow in report_list:
        if incident_workflow.workflow.name not in incident_workflows_answer:
            incident_workflows_answer[incident_workflow.workflow.name] = dict()
        if incident_workflow.workflow.name not in incident_workflows_impact:
            incident_workflows_impact[incident_workflow.workflow.name] = []

        answers = Answer.objects.all().filter(incident_workflow=incident_workflow)
        for answer in answers.all():
            populate_questions_answers(
                answer,
                incident_workflows_answer[incident_workflow.workflow.name],
            )
        # impacts
        for impact in incident_workflow.impacts.all():
            incident_workflows_impact[incident_workflow.workflow.name].append(impact)
    # Render the HTML file
    output_from_parsed_template = render_to_string(
        "report/template.html",
        {
            "incident": incident,
            "incident_workflows_answer": incident_workflows_answer,
            "incident_workflows_impact": incident_workflows_impact,
            "regulation": incident.sector_regulation.regulation,
            "sectors": sectors,
        },
        request=request,
    )

    base_url = os.path.join(BASE_DIR, "incidents/templates/report")
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

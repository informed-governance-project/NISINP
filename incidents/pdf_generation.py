import os
from typing import Dict, List

from django.conf import settings
from django.http import HttpRequest
from django.template.loader import render_to_string
from weasyprint import CSS, HTML

from .models import Answer, Incident, IncidentWorkflow


def get_pdf_report(
    incident: Incident, incident_workflow: IncidentWorkflow, request: HttpRequest
):
    # TO DO : improve for more than 2 level ?
    sectors: Dict[str, List[str]] = {}

    for sector in incident.affected_sectors.all():
        sector_name = sector.get_safe_translation()

        if sector.parent:
            parent_name = sector.parent.get_safe_translation()
            sectors.setdefault(parent_name, []).append(sector_name)
        else:
            if sector_name not in sectors:
                sectors[sector_name] = []

    incident_workflows_answer: Dict[str, Dict[str, str, List[str]]] = {}
    incident_workflows_impact: Dict[str, List[str]] = {}
    # display for the full incident or just a report
    if incident_workflow is None:
        report_list = incident.get_latest_incident_workflows()
    else:
        report_list = [incident_workflow]

    for incident_workflow in report_list:
        workflow_name = incident_workflow.workflow
        incident_workflows_answer.setdefault(workflow_name, dict())
        incident_workflows_impact.setdefault(workflow_name, [])

        answers = Answer.objects.filter(incident_workflow=incident_workflow).order_by(
            "question_options__position"
        )
        for answer in answers:
            populate_questions_answers(
                answer,
                incident_workflows_answer[workflow_name],
            )
        # impacts
        incident_workflows_impact[workflow_name].extend(incident_workflow.impacts.all())

    # Render the HTML file

    static_theme_dir = settings.STATIC_THEME_DIR

    output_from_parsed_template = render_to_string(
        "report/template.html",
        {
            "static_theme_dir": os.path.abspath(static_theme_dir),
            "incident": incident,
            "incident_workflows_answer": incident_workflows_answer,
            "incident_workflows_impact": incident_workflows_impact,
            "sectors": sectors,
        },
        request=request,
    )

    htmldoc = HTML(string=output_from_parsed_template, base_url=static_theme_dir)

    stylesheets = [
        CSS(os.path.join(static_theme_dir, "css/custom.css")),
        CSS(os.path.join(static_theme_dir, "css/report.css")),
    ]

    return htmldoc.write_pdf(stylesheets=stylesheets)


def populate_questions_answers(answer: Answer, preliminary_questions_answers: Dict):
    category_label = answer.question_options.category
    question_label = answer.question_options.question
    question_dict = preliminary_questions_answers.setdefault(category_label, {})
    answer_list = question_dict.setdefault(question_label, [])

    predefined_answers = [
        pa.predefined_answer for pa in answer.predefined_answer_options.all()
    ]

    if predefined_answers:
        answer_list.extend(predefined_answers)
    else:
        answer_list.append(answer.answer)

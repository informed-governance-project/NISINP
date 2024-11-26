import os
from typing import Dict, List

from django.conf import settings
from django.http import HttpRequest
from django.template.loader import render_to_string
from weasyprint import CSS, HTML

from theme.globals import REGIONAL_AREA
from django_countries import countries

from .models import Answer, Incident, IncidentWorkflow


def get_pdf_report(
    incident: Incident, incident_workflow: IncidentWorkflow, request: HttpRequest
):
    # TO DO : improve for more than 2 level ?
    sectors: Dict[str, List[str]] = {}
    # boolean to see if it's report or incident
    report_name = None

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
        report_name = incident_workflow.workflow.name

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
        incident_workflows_impact[workflow_name].extend(
            incident_workflow.impacts.all().order_by("translations__label").distinct()
        )
        incident_workflows_impact[workflow_name] = list({impact.id: impact for impact in incident_workflows_impact[workflow_name]}.values())

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
            "report_name": report_name,
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
    category_label = answer.question_options.category_option.question_category
    question_label = answer.question_options.question
    question_dict = preliminary_questions_answers.setdefault(category_label, {})
    answer_list = question_dict.setdefault(question_label, [])

    if answer.predefined_answers.all():
        answer_list.extend(answer.predefined_answers.all())
    else:
        answer_string = answer
        if answer.question_options.question.question_type == "RL":
            REGIONAL_AREA_DICT = dict(REGIONAL_AREA)
            region_name_list = [
                REGIONAL_AREA_DICT.get(region_code, region_code)
                for region_code in filter(None, str(answer).split(","))
            ]
            answer_string = " - ".join(map(str, region_name_list))
        if answer.question_options.question.question_type == "CL":
            COUNTRY_DICT = dict(countries)
            region_name_list = [
                COUNTRY_DICT.get(region_code, region_code)
                for region_code in filter(None, str(answer).split(","))
            ]
            answer_string = " - ".join(map(str, region_name_list))
        answer_list.append(answer_string)

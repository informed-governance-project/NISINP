from django import template
from django.utils.translation import gettext as _

register = template.Library()


@register.filter
def get_class_name(value):
    return value.__class__.__name__


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def index(indexable, i):
    return indexable[int(i)]


@register.filter()
def translate(text):
    return _(text)


@register.simple_tag
def status_class(value):
    if value == "PASS":
        return "table-success"
    elif value == "FAIL":
        return "table-danger"
    elif value == "DELIV":
        return "table-info"
    elif value == "OUT":
        return "table-secondary"
    else:
        return ""


@register.filter
def filter_workflows(incidentWorkflows, report_id):
    return [
        incidentworkflow
        for incidentworkflow in incidentWorkflows
        if incidentworkflow.workflow.pk == report_id
    ]


@register.simple_tag
def is_workflow_disabled(allWorkflows, incidentWorkflows, report):
    current_index = allWorkflows.index(report)

    if not incidentWorkflows and not current_index == 0:
        return True

    workflow_list = [workflow.workflow for workflow in incidentWorkflows]

    if (
        current_index < len(allWorkflows) - 1
        and allWorkflows[current_index + 1] in workflow_list
    ):
        return True

    if (
        current_index == len(allWorkflows) - 1
        and allWorkflows[current_index - 1] not in workflow_list
    ):
        return True

    return False

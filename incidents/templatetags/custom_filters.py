import json

from django import template
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.translation import gettext as _

from incidents.models import IncidentWorkflow

register = template.Library()


@register.filter
def get_class_name(value):
    return value.__class__.__name__


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter(name="split")
def split(value, key):
    return value.split(key)


@register.filter
def index(indexable, i):
    return indexable[int(i)]


@register.filter()
def translate(text):
    return _(text)


# get the incident workflow by workflow and incident to see the historic for operator
@register.filter
def get_incident_workflow_by_workflow(incident, workflow):
    queryset = IncidentWorkflow.objects.filter(
        incident=incident, workflow=workflow
    ).order_by("-timestamp")

    if not queryset:
        return None

    data = list(queryset.values("id", "timestamp"))
    for item in data:
        item["timestamp"] = item["timestamp"].isoformat()

    return json.dumps(data, cls=DjangoJSONEncoder)


# get settings value
@register.simple_tag
def settings_value(name):
    return getattr(settings, name, "")


@register.filter
def range_list(value):
    return range(1, int(value) + 1)

from django import template
from django.conf import settings

register = template.Library()


# replace a field in the URL, used for filter + pagination
@register.simple_tag
def url_replace(request, field, value):
    d = request.GET.copy()
    d[field] = value
    return d.urlencode()


# get settings value
@register.simple_tag
def settings_value(name):
    return getattr(settings, name, "")


@register.simple_tag
def status_class(value):
    if value == "PASS":
        return "table-success"
    elif value == "FAIL":
        return "table-danger"
    elif value == "DELIV":
        return "table-info"
    elif value == "OUT":
        return "table-dark"
    else:
        return "table-secondary"

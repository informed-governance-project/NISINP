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
        return "border border-passed border-2"
    elif value == "PASSM":
        return "bg-passed"
    elif value == "FAIL":
        return "border border-failed border-2"
    elif value == "FAILM":
        return "bg-failed "
    elif value == "DELIV":
        return "bg-under-review"
    elif value == "OUT":
        return "table-dark"
    else:
        return "table-secondary"


@register.simple_tag
def status_icon(value):
    if value == "PASS":
        return "custom-icon-passed"
    elif value == "PASSM":
        return "custom-icon-passed-sent"
    elif value == "FAIL":
        return "custom-icon-failed"
    elif value == "FAILM":
        return "custom-icon-failed-sent"
    elif value == "DELIV":
        return "custom-icon-under-review-white"
    elif value == "OUT":
        return "table-dark"
    else:
        return "table-secondary"

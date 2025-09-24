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


@register.simple_tag(takes_context=True)
def status_class(context, value):
    if value == "PASS":
        if context["is_regulator"]:
            return "border border-passed border-2"
        return "bg-passed"
    elif value == "PASSM":
        return "bg-passed"
    elif value == "FAIL":
        if context["is_regulator"]:
            return "border border-failed border-2"
        return "bg-failed "
    elif value == "FAILM":
        return "bg-failed "
    elif value == "DELIV":
        return "bg-under-review"
    else:
        return "bg-unsubmitted"


@register.simple_tag(takes_context=True)
def status_icon(context, value):
    if value == "PASS":
        if context["is_regulator"]:
            return "custom-icon-passed"
        return "custom-icon-passed-white"
    elif value == "PASSM":
        if context["is_regulator"]:
            return "custom-icon-passed-sent"
        return "custom-icon-passed-white"
    elif value == "FAIL":
        if context["is_regulator"]:
            return "custom-icon-failed"
        return "custom-icon-failed-white"
    elif value == "FAILM":
        if context["is_regulator"]:
            return "custom-icon-failed-sent"
        return "custom-icon-failed-white"
    elif value == "DELIV":
        return "custom-icon-under-review-white"
    else:
        return "custom-icon-unsubmitted-white"


@register.filter
def split(value, delimiter=","):
    """Splits the string by delimiter."""
    return value.split(delimiter)

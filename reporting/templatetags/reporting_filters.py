from django import template
from django.conf import settings

register = template.Library()


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def index(indexable, i):
    try:
        return indexable[int(i)]
    except (IndexError, ValueError):
        return None


# get settings value
@register.simple_tag
def settings_value(name):
    return getattr(settings, name, "")


@register.filter
def range_list(value):
    return range(int(value))


@register.simple_tag
def security_objective_exists(instance, year, sector):
    return instance.security_objective_exists(year, sector)


@register.simple_tag
def risk_analysis_exists(instance, year, sector):
    return instance.risk_analysis_exists(year, sector)


@register.simple_tag
def get_report_recommandations(instance, year, sector):
    return instance.get_report_recommandations(year, sector)

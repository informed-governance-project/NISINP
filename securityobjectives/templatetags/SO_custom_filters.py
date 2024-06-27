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
def get_completion(standard_answer):
    if standard_answer.is_finished:
        return _("Finished")
    else:
        if standard_answer.securitymeasureanswers.count() == 0:
            return _("Not started")
    return _("Work in progress")


@register.simple_tag
def get_url(standard_answer):
    if standard_answer.is_finished:
        return '#'
    else:
        if standard_answer.securitymeasureanswers.count() == 0:
            return "create_so/"+str(standard_answer.id)
    return "create_so/"+str(standard_answer.id)


# replace a field in the URL, used for filter + pagination
@register.simple_tag
def url_replace(request, field, value):
    d = request.GET.copy()
    d[field] = value
    return d.urlencode()

from django.forms.widgets import TextInput
import datetime


class TempusDominusV6Widget(TextInput):
    template_name = 'widgets/tempus_dominus_v6.html'

    def __init__(self, attrs=None, max_date=None):
        self.max_date = max_date
        default_attrs = {
            'class': 'form-control datetimepicker-input',
            'data-td-target': '#%(id)s',
            'autocomplete': 'off'
        }
        if max_date:
            default_attrs['data-max-date'] = max_date
        else:
            default_attrs['data-max-date'] = datetime.date.today().isoformat()
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['widget']['td_id'] = attrs['id']
        return context

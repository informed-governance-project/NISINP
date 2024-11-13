from django import forms
from django.utils import timezone
from django.utils.translation import gettext as _

from incidents.forms import DropdownCheckboxSelectMultiple

# from .models import RiskAnalysisJson


# to upload the JSON
# class RiskAnalysisSubmissionForm(forms.Form):
#     files = forms.FileField(
#         widget=forms.TextInput(
#             attrs={
#                 "type": "File",
#                 "multiple": "True",
#             }
#         )
#     )

# class Meta:
#     model = RiskAnalysisJson
#     fields = ["data"]
#     labels = {
#         "data": _("Upload JSON File"),
#     }
#     widgets = {
#         "data": forms.FileInput(attrs={"accept": ".json"}),
#     }


class ImportRiskAnalysisForm(forms.Form):
    import_file = forms.FileField(
        required=True,
    )

    company = forms.ChoiceField(
        widget=forms.Select(),
        required=True,
        label=_("Company"),
    )

    year = forms.ChoiceField(
        widget=forms.Select(),
        choices=[
            (year, year)
            for year in range(timezone.now().year - 3, timezone.now().year + 2)
        ],
        required=True,
        initial=timezone.now().year,
        label=_("Year"),
    )

    sectors = forms.MultipleChoiceField(
        required=True,
        widget=DropdownCheckboxSelectMultiple(
            attrs={"data-selected-text-format": "count > 3"}
        ),
        label=_("Sectors"),
    )

    def __init__(self, *args, **kwargs):
        initial = kwargs.pop("initial", None)
        super().__init__(*args, **kwargs)
        if initial["company"] and initial["sectors"]:
            self.fields["company"].choices = initial["company"]
            self.fields["sectors"].choices = initial["sectors"]
        else:
            self.fields["company"].disabled = True
            self.fields["year"].disabled = True
            self.fields["sectors"].disabled = True

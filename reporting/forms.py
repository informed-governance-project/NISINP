from django import forms

from .models import RiskAnalysisJson


# to upload the JSON
class RiskAnalysisSubmissionForm(forms.ModelForm):

    JSON_file = forms.FileField()
    data = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = RiskAnalysisJson
        fields = [
           "data"
        ]

from django import forms

from governanceplatform.models import Regulation, Regulator


class RegulationForm(forms.Form):
    regulations = forms.MultipleChoiceField(
        required=True,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "multiple-selection"}),
    )

    def __init__(self, *args, **kwargs):
        regulators = kwargs["initial"].get("regulators", None)
        super().__init__(*args, **kwargs)

        if regulators is not None:
            self.fields["regulations"].choices = construct_regulation_array(
                regulators.all()
            )


# prepare an array of regulations
def construct_regulation_array(regulators):
    regulations_to_select = []
    regulations = Regulation.objects.all().filter(regulators__in=regulators)

    for regulation in regulations:
        regulations_to_select.append([regulation.id, regulation.label])

    return regulations_to_select


class RegulatorForm(forms.Form):
    # generic impact definitions
    regulators = forms.MultipleChoiceField(
        required=True,
        choices=[],
        widget=forms.CheckboxSelectMultiple(attrs={"class": "multiple-selection"}),
        label="Send security objectives to:",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.fields["regulators"].choices = [(k.id, k.name + " " + k.full_name) for k in Regulator.objects.all()]
        except Exception:
            self.fields["regulators"].choices = []

    def get_selected_data(self):
        return self.fields["regulators"].initial


def get_forms_list(standard=None):
    category_tree = []
    if standard is None:
        category_tree = [
            RegulatorForm,
            RegulationForm,
        ]

    return category_tree

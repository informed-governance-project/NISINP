from django import forms

from governanceplatform.models import Regulation, Regulator
from .models import Standard


class RegulationForm(forms.Form):
    regulations = forms.ChoiceField(
        required=True,
        widget=forms.RadioSelect(attrs={"class": "multiple-selection"}),
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

    try:
        regulations_standard_ids = [
            r
            for r in Standard.objects.values_list("regulation", flat=True).filter(regulator__in=regulators).distinct()
        ]
        regulations_to_select = [
            (k.id, k.label)
            for k in Regulation.objects.filter(id__in=regulations_standard_ids)
        ]
    except Exception:
        regulations_to_select = []

    return regulations_to_select


class RegulatorForm(forms.Form):
    regulators = forms.ChoiceField(
        required=True,
        choices=[],
        widget=forms.RadioSelect(attrs={"class": "multiple-selection"}),
        label="Send security objectives to:",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            regulators_standard_ids = [
                r
                for r in Standard.objects.values_list("regulator", flat=True).distinct()
            ]
            self.fields["regulators"].choices = [
                (k.id, k.name + " " + k.full_name)
                for k in Regulator.objects.filter(id__in=regulators_standard_ids)
            ]
        except Exception:
            self.fields["regulators"].choices = []

    def get_selected_data(self):
        return self.fields["regulators"].initial


class StandardForm(forms.Form):
    standard = forms.ChoiceField(
        required=True,
        widget=forms.RadioSelect(attrs={"class": "multiple-selection"}),
    )

    def __init__(self, *args, **kwargs):
        regulators = kwargs["initial"].get("regulators", None)
        regulations = kwargs["initial"].get("regulations", None)
        super().__init__(*args, **kwargs)

        if regulators is not None and regulations is not None:
            self.fields["standard"].choices = construct_standard_array(
                regulators.all(),
                regulations.all()
            )


# prepare an array of regulations
def construct_standard_array(regulators, regulations):
    standards_to_select = []
    standards = Standard.objects.all().filter(regulator__in=regulators, regulation__in=regulations).distinct()

    for standard in standards:
        standards_to_select.append([standard.id, standard.label])

    return standards_to_select


def get_forms_list(standard_answer=None):
    category_tree = []
    if standard_answer is None:
        category_tree = [
            RegulatorForm,
            RegulationForm,
            StandardForm,
        ]
    else:
        security_objectives = standard_answer.standard.securityobjective_set
        print(standard_answer)
        print(standard_answer.standard)
        print(security_objectives)

    return category_tree

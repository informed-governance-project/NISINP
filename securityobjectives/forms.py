from django import forms
from django.utils.translation import gettext as _


class SecurityObjectiveAnswerForm(forms.Form):
    is_measure_in_place = forms.BooleanField()
    operator_comment = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 2,
                "placeholder": "",
                # "onblur": "onBlurTextarea(this)",
            }
        ),
    )
    regulator_comment = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 2,
                "placeholder": "",
                # "onblur": "onBlurTextarea(this)",
            }
        ),
    )


class CustomSelect(forms.Select):
    def create_option(
        self, name, value, label, selected, index, subindex=None, attrs=None
    ):
        option = super().create_option(
            name, value, label, selected, index, subindex=subindex, attrs=attrs
        )

        if value == "NOT_REVIEWED":
            option["attrs"]["class"] = "bg-transparent"
        elif value == "PASS":
            option["attrs"]["class"] = "bg-success"
        elif value == "FAIL":
            option["attrs"]["class"] = "bg-danger"

        return option


class SecurityObjectiveStatusForm(forms.Form):
    security_objective_status = forms.ChoiceField(
        choices=[
            ("NOT_REVIEWED", _("Not reviewed")),
            ("PASS", _("Pass")),
            ("FAIL", _("Fail")),
        ],
        widget=CustomSelect(),
        initial="NOT_REVIEWED",
    )

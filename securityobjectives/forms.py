from django import forms


class SecurityObjectiveAnswerForm(forms.Form):
    is_measure_in_place = forms.BooleanField()
    operator_comment = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 2,
                "placeholder": ""
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

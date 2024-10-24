from django import forms
from django.utils import timezone
from django.utils.translation import gettext as _

from incidents.globals import REVIEW_STATUS


class SecurityObjectiveAnswerForm(forms.Form):
    is_implemented = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "onclick": "update_so_answer(this)",
            }
        ),
    )
    comment = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 2,
                "placeholder": "",
                "onblur": "update_so_answer(this)",
            }
        ),
    )
    review_comment = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 2,
                "placeholder": "",
                "onblur": "update_so_answer(this)",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        initial = kwargs.get("initial", None)
        super().__init__(*args, **kwargs)
        if initial:
            self.fields["is_implemented"].disabled = initial.get("is_regulator", True)
            self.fields["comment"].disabled = initial.get("is_regulator", True)
            self.fields["review_comment"].disabled = not initial.get(
                "is_regulator", True
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


class SelectSOStandardForm(forms.Form):
    so_standard = forms.ChoiceField(
        widget=forms.Select(),
        required=True,
        label=_("Standard"),
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

    def __init__(self, *args, **kwargs):
        initial = kwargs.pop("initial", None)
        super().__init__(*args, **kwargs)
        if initial:
            self.fields["so_standard"].choices = initial
        else:
            self.fields["so_standard"].disabled = True
            self.fields["year"].disabled = True


class ImportSOForm(forms.Form):
    import_file = forms.FileField()

    standard = forms.ChoiceField(
        widget=forms.Select(),
        required=True,
        label=_("Standard"),
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

    status = forms.ChoiceField(
        widget=forms.Select(),
        choices=REVIEW_STATUS,
        initial=REVIEW_STATUS[0][0],
        label=_("Status"),
    )

    def __init__(self, *args, **kwargs):
        initial = kwargs.pop("initial", None)
        super().__init__(*args, **kwargs)
        if initial["standard"] and initial["company"]:
            self.fields["standard"].choices = initial["standard"]
            self.fields["company"].choices = initial["company"]
        else:
            self.fields["standard"].disabled = True
            self.fields["company"].disabled = True
            self.fields["year"].disabled = True
            self.fields["status"].disabled = True


class SelectYearForm(forms.Form):
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

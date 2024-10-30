from django import forms
from django.utils import timezone
from django.utils.translation import gettext as _

from .models import SecurityObjectiveStatus


class SecurityObjectiveAnswerForm(forms.Form):
    is_implemented = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "onclick": "update_so_declaration(this)",
            }
        ),
    )
    comment = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 2,
                "placeholder": "",
                "onblur": "update_so_declaration(this)",
            }
        ),
    )
    review_comment = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 2,
                "placeholder": "",
                "onblur": "update_so_declaration(this)",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        initial = kwargs.get("initial", None)
        super().__init__(*args, **kwargs)
        if initial:
            is_regulator = initial.get("is_regulator", True)
            self.fields["is_implemented"].disabled = is_regulator
            self.fields["comment"].disabled = is_regulator
            self.fields["review_comment"].disabled = not is_regulator
            if not is_regulator:
                self.fields["review_comment"].widget = forms.HiddenInput()
                self.initial["review_comment"] = None


class SecurityObjectiveStatusForm(forms.ModelForm):
    class Meta:
        model = SecurityObjectiveStatus
        fields = ["status"]
        widgets = {
            "status": forms.Select(attrs={"onchange": "update_so_declaration(this)"}),
        }


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
    import_file = forms.FileField(
        required=True,
    )

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

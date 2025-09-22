from django import forms
from django.utils import timezone
from django.utils.translation import gettext as _

from incidents.forms import DropdownCheckboxSelectMultiple
from incidents.widgets import TempusDominusV6Widget

from .models import SecurityObjectiveStatus, StandardAnswer


class SecurityObjectiveAnswerForm(forms.Form):
    is_implemented = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "onclick": "update_so_declaration(this)",
            }
        ),
    )
    justification = forms.CharField(
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

        def set_readonly(field_name):
            field = self.fields[field_name]
            field_classes = field.widget.attrs.get("class", "")
            field.widget.attrs.update({"class": f"{field_classes} readonly_field"})
            field.disabled = True

        if initial:
            is_readonly = initial.get("is_readonly", True)
            is_regulator = initial.get("is_regulator", True)

            if is_readonly or is_regulator:
                set_readonly("is_implemented")
                set_readonly("justification")

            if is_readonly:
                set_readonly("review_comment")
            elif not is_regulator:
                self.fields["review_comment"].widget = forms.HiddenInput()
                self.initial["review_comment"] = None


class SecurityObjectiveStatusForm(forms.ModelForm):
    class Meta:
        model = SecurityObjectiveStatus
        fields = ["status", "actions"]
        widgets = {
            "status": forms.Select(
                attrs={
                    "class": "so_status_form",
                    "onchange": "update_so_declaration(this)",
                }
            ),
            "actions": forms.Textarea(
                attrs={
                    "class": "so_actions_form",
                    "placeholder": "",
                    "onchange": "update_so_declaration(this)",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        initial = kwargs.get("initial", None)
        super().__init__(*args, **kwargs)

        def set_readonly(field_name):
            field = self.fields[field_name]
            field_classes = field.widget.attrs.get("class", "")
            field.widget.attrs.update({"class": f"{field_classes} readonly_field"})
            field.disabled = True

        self.fields["status"].required = False
        self.fields["actions"].required = False

        if initial:
            is_readonly = initial.get("is_readonly", True)
            is_regulator = initial.get("is_regulator", True)
            current_classes = self.fields["status"].widget.attrs.get("class", "")
            new_classes = current_classes

            if is_readonly:
                set_readonly("status")
                set_readonly("actions")

            if is_regulator:
                set_readonly("actions")

            if initial["status"] == "PASS":
                new_classes = f"{current_classes} text-white bg-passed"

            if initial["status"] == "FAIL":
                new_classes = f"{current_classes} text-white bg-failed"

            self.fields["status"].widget.attrs.update(
                {"class": new_classes},
            )


class SelectSOStandardForm(forms.Form):
    so_standard = forms.ChoiceField(
        widget=forms.Select(),
        required=True,
        label=_("Evaluation Framework"),
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
        if initial:
            self.fields["so_standard"].choices = initial["standard_list"]
            self.fields["sectors"].choices = initial["sectors_list"]
        else:
            self.fields["so_standard"].disabled = True
            self.fields["year"].disabled = True
            self.fields["sectors"].disabled = True


class ImportSOForm(forms.Form):
    import_file = forms.FileField(
        required=True,
    )

    standard = forms.ChoiceField(
        widget=forms.Select(),
        required=True,
        label=_("Evaluation Framework"),
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
        choices = kwargs.pop("choices", {})
        super().__init__(*args, **kwargs)

        if (
            choices.get("standard")
            and choices.get("company")
            and choices.get("sectors")
        ):
            self.fields["standard"].choices = choices["standard"]
            self.fields["company"].choices = choices["company"]
            self.fields["sectors"].choices = choices["sectors"]
        else:
            for field_name in ["standard", "company", "year", "sectors"]:
                self.fields[field_name].disabled = True


class CopySOForm(forms.Form):
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
        if initial["sectors"]:
            self.fields["sectors"].choices = initial["sectors"]
        else:
            self.fields["year"].disabled = True
            self.fields["sectors"].disabled = True


class ReviewForm(forms.ModelForm):
    class Meta:
        model = StandardAnswer
        fields = ["review_comment", "deadline", "status"]
        widgets = {
            "review_comment": forms.Textarea(
                attrs={
                    "rows": 3,
                }
            ),
            "deadline": TempusDominusV6Widget(),
        }

    def __init__(self, *args, **kwargs):
        initial = kwargs.get("initial", None)
        super().__init__(*args, **kwargs)
        self.fields["review_comment"].required = True
        self.fields["deadline"].required = False
        self.fields["status"].required = False
        self.fields["status"].disabled = True

        if initial:
            current_classes = self.fields["status"].widget.attrs.get("class", "")
            is_read_only = initial.get("is_readonly", True)
            self.fields["review_comment"].disabled = is_read_only
            self.fields["deadline"].disabled = is_read_only
            new_classes = f"{current_classes} fw-bolder text-white"

            if initial["status"] == "PASS":
                new_classes = f"{new_classes} bg-passed"

            if initial["status"] == "FAIL":
                new_classes = f"{new_classes} bg-failed"

            self.fields["status"].widget.attrs.update(
                {"class": new_classes},
            )

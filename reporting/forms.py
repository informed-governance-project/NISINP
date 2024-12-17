from django import forms
from django.forms import BaseModelFormSet, modelformset_factory
from django.utils import timezone
from django.utils.translation import gettext as _
from parler.forms import TranslatableModelForm

from governanceplatform.models import Company, Sector
from incidents.forms import DropdownCheckboxSelectMultiple

from .models import ObservationRecommendation, SectorReportConfiguration

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


class ReportGenerationForm(forms.Form):
    company = forms.ChoiceField(
        required=True,
        label=_("Company"),
    )

    year = forms.ChoiceField(
        choices=[
            (year, year)
            for year in range(timezone.now().year - 2, timezone.now().year + 1)
        ],
        required=True,
        initial=timezone.now().year,
        label=_("Year"),
    )

    sector = forms.ChoiceField(
        required=True,
        label=_("Sector"),
    )

    nb_years = forms.ChoiceField(
        choices=[(str(nb_year), str(nb_year)) for nb_year in range(1, 4)],
        required=True,
        label=_("Number of years to compare"),
    )

    so_exclude = forms.MultipleChoiceField(
        widget=DropdownCheckboxSelectMultiple(
            attrs={"data-selected-text-format": "count > 3"}
        ),
        required=False,
        label=_("Security objectives to exclude"),
    )

    def __init__(self, *args, **kwargs):
        initial = kwargs.pop("initial", None)
        super().__init__(*args, **kwargs)
        if initial["company"]:
            self.fields["company"].choices = initial["company"]
        if initial["sectors"]:
            self.fields["sector"].choices = initial["sectors"]
        if initial["so"]:
            self.fields["so_exclude"].choices = initial["so"]

        if not initial["company"] and not initial["sector"]:
            self.fields["company"].disabled = True
            self.fields["year"].disabled = True
            self.fields["sector"].disabled = True


class ConfigurationReportForm(forms.ModelForm):
    class Meta:
        model = SectorReportConfiguration
        fields = "__all__"

    def __init__(self, *args, user=None, **kwargs):
        initial = kwargs.get("initial", {})
        instance = kwargs.get("instance", None)
        super().__init__(*args, **kwargs)

        self.fields["so_excluded"].required = False
        self.fields["so_excluded"].queryset = self.fields[
            "so_excluded"
        ].queryset.order_by("unique_code")

        sectors = initial.get("sectors")
        if sectors:
            self.fields["sector"].queryset = sectors

        if instance and instance.pk:
            self.fields["sector"].disabled = True

    def save(self, commit=True):
        # Save the instance first
        instance = super().save(commit=False)

        # Save the ManyToMany field separately
        if commit:
            instance.save()  # Save the instance if commit=True
            self.save_m2m()  # Save M2M fields explicitly

        return instance


class CompanySelectForm(forms.ModelForm):
    selected = forms.BooleanField(required=False, widget=forms.CheckboxInput)
    year = forms.IntegerField(required=False)
    sector = forms.ModelChoiceField(
        queryset=Sector.objects.all(), required=False, widget=forms.HiddenInput()
    )

    class Meta:
        model = Company
        fields = ["id", "selected", "name", "sector"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].widget = forms.HiddenInput()


class CompanySelectFormSet(BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        self.year = kwargs.pop("year", None)
        self.sectors_filter = kwargs.pop("sectors_filter", None)
        queryset = kwargs.get("queryset")
        self.company_sectors = []

        if queryset:
            for company in queryset:
                for sector in company.get_queryset_sectors():
                    if not self.sectors_filter or str(sector.id) in self.sectors_filter:
                        self.company_sectors.append(
                            {"company": company, "sector": sector}
                        )

        kwargs["queryset"] = Company.objects.none()
        super().__init__(*args, **kwargs)

        self._update_management_form()

    def validate_unique(self):
        company_sector_pairs = [
            (form.cleaned_data.get("id"), form.cleaned_data.get("sector"))
            for form in self.forms
        ]

        seen = set()
        errors = []
        for company, sector in company_sector_pairs:
            if (company.id, sector) in seen:
                errors.append("Please correct the duplicate company-sector values.")
            seen.add((company.id, sector))

        if errors:
            raise forms.ValidationError(errors)

    def add_fields(self, form, index):
        super().add_fields(form, index)

        if self.year:
            form.initial["year"] = self.year

    def total_form_count(self):
        return len(self.company_sectors)

    def _update_management_form(self):
        total_forms = len(self.company_sectors)
        self.management_form.initial["TOTAL_FORMS"] = total_forms
        self.management_form.initial["INITIAL_FORMS"] = total_forms

    def _construct_form(self, i, **kwargs):
        if i < len(self.company_sectors):
            company_sector = self.company_sectors[i]
            company = company_sector["company"]
            sector = company_sector["sector"]

            kwargs["initial"] = {
                "sector": sector,
                "id": company.id,
                "name": company.name,
            }
            kwargs["instance"] = company
        return super()._construct_form(i, **kwargs)


CompanySelectFormSet = modelformset_factory(
    Company, form=CompanySelectForm, formset=CompanySelectFormSet, extra=0
)


class RecommendationsSelectForm(TranslatableModelForm):
    selected = forms.BooleanField(required=False, widget=forms.CheckboxInput)

    class Meta:
        model = ObservationRecommendation
        fields = ["id", "selected", "code", "description", "sectors"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["code"].required = False
        self.fields["sectors"].required = False


RecommendationsSelectFormSet = modelformset_factory(
    ObservationRecommendation, form=RecommendationsSelectForm, extra=0
)

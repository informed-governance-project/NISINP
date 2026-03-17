from django import forms
from django.conf import settings
from django.forms import BaseModelFormSet, modelformset_factory
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from parler.forms import TranslatableModelForm

from governanceplatform.helpers import get_sectors_grouped
from governanceplatform.models import Company, Regulation, Sector
from incidents.forms import DropdownCheckboxSelectMultiple
from securityobjectives.models import Standard

from .models import (
    CompanyReporting,
    ObservationRecommendation,
    ObservationRecommendationThrough,
    Project,
    SectorReportConfiguration,
    Template,
)


class ImportRiskAnalysisForm(forms.Form):
    import_file = forms.FileField(
        widget=forms.FileInput(attrs={"accept": ".json"}),
        required=True,
        label=_("JSON File"),
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

        if choices.get("company") and choices.get("sectors"):
            self.fields["company"].choices = choices["company"]
            self.fields["sectors"].choices = choices["sectors"]
        else:
            for field_name in ["company", "year", "sectors"]:
                self.fields[field_name].disabled = True


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


class CompanySelectForm(forms.ModelForm):
    selected = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "company-select-checkbox"}),
    )
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

    def validate_unique(self):
        return


class CompanySelectFormSet(BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        self.year = kwargs.pop("year", None)
        self.sectors_filter = kwargs.pop("sectors_filter", None)
        queryset = kwargs.get("queryset")
        self.company_sectors = []

        if queryset:
            for company in queryset:
                for sector in Sector.objects.all():
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
            if company is not None:
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
                "object": company,
                "id": company.id,
                "name": company.name,
            }
        return super()._construct_form(i, **kwargs)


CompanySelectFormSet = modelformset_factory(
    Company, form=CompanySelectForm, formset=CompanySelectFormSet, extra=0
)


class RecommendationsSelectForm(TranslatableModelForm):
    selected = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "recommendation-select-checkbox"}),
    )

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


class ReviewCommentForm(forms.ModelForm):
    class Meta:
        model = CompanyReporting
        fields = ["id", "comment"]


class ObservationRecommendationOrderForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["order"].widget.attrs = {
            "class": "reporting-input-field",
            "data-recommendation-id": self.instance.pk,
        }

    class Meta:
        model = ObservationRecommendationThrough
        fields = ["order"]


class TemplateAdminForm(forms.ModelForm):
    template_file = forms.FileField(
        required=True,
        widget=forms.FileInput(attrs={"accept": ".docx"}),
    )

    class Meta:
        model = Template
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["language"] = forms.ChoiceField(
            choices=settings.LANGUAGES,
        )

    def clean_template_file(self):
        file = self.cleaned_data.get("template_file")
        if isinstance(file, (memoryview, bytes)):
            return bytes(file)
        if file:
            if not file.name.endswith(".docx"):
                raise forms.ValidationError(_("Only .docx files are allowed."))
            return file.read()
        existing = self.instance.template_file
        if existing:
            return bytes(existing)
        return None


class CreateProjectForm(forms.ModelForm):
    name = forms.CharField(
        required=True,
        label=_("Project name"),
    )

    regulation = forms.ModelChoiceField(
        queryset=Regulation.objects.none(),
        required=True,
        label=_("Regulation"),
    )

    standard = forms.ModelChoiceField(
        queryset=Standard.objects.none(),
        required=True,
        label=_("Standard"),
    )

    reference_year = forms.ChoiceField(
        choices=[
            (year, year)
            for year in range(timezone.now().year - 10, timezone.now().year + 2)
        ],
        required=True,
        label=_("Reference year"),
    )

    years = forms.MultipleChoiceField(
        widget=DropdownCheckboxSelectMultiple(),
        choices=[
            (year, year)
            for year in range(timezone.now().year - 10, timezone.now().year + 2)
        ],
        required=True,
        label=_("Year comparaison"),
    )

    sectors = forms.MultipleChoiceField(
        required=True,
        widget=DropdownCheckboxSelectMultiple(),
        label=_("Sectors"),
    )

    selected_languages = forms.MultipleChoiceField(
        required=True,
        widget=DropdownCheckboxSelectMultiple(),
        label=_("Languages"),
    )

    class Meta:
        model = Project
        fields = [
            "name",
            "regulation",
            "standard",
            "reference_year",
            "years",
            "sectors",
            "top_ranking",
            "threshold_for_high_risk",
            "selected_file_format",
            "selected_languages",
        ]

    def clean_years(self):
        data = self.cleaned_data["years"]
        # convert str to int
        return [int(y) for y in data]

    def __init__(self, *args, **kwargs):
        choices = kwargs.pop("choices", {})
        is_copy = kwargs.pop("is_copy", False)
        super().__init__(*args, **kwargs)

        self.fields["selected_languages"].choices = settings.LANGUAGES

        regulation_qs = choices.get("regulations", Regulation.objects.all())
        standard_qs = choices.get("standards", Standard.objects.all())
        sector_choices = get_sectors_grouped(Sector.objects.all())

        self.fields["regulation"].queryset = regulation_qs
        self.fields["standard"].queryset = standard_qs
        self.fields["sectors"].choices = sector_choices

        if self.instance and self.instance.pk:
            project = self.instance

            self.initial["regulation"] = project.standard.regulation
            self.initial["standard"] = project.standard

            # M2M sectors
            self.initial["sectors"] = list(project.sectors.values_list("id", flat=True))

            if is_copy:
                disabled_fields = [
                    "regulation",
                    "standard",
                    "reference_year",
                    "years",
                    "sectors",
                    "top_ranking",
                    "threshold_for_high_risk",
                    "selected_file_format",
                    "selected_languages",
                ]
            else:
                disabled_fields = ["regulation", "standard"]

            for field_name in disabled_fields:
                self.fields[field_name].disabled = True

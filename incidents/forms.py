from datetime import datetime

import pytz
from bootstrap_datepicker_plus.widgets import DateTimePickerInput
from django import forms
from django.db.models import Q
from django.forms.widgets import ChoiceWidget
from django.utils.translation import gettext_lazy as _
from django_countries import countries
from django_otp.forms import OTPAuthenticationForm
from parler.widgets import SortedCheckboxSelectMultiple

from governanceplatform.helpers import (
    get_active_company_from_session,
    is_user_regulator,
)
from governanceplatform.models import Regulation, Regulator, Sector, Service
from governanceplatform.settings import TIME_ZONE

from .globals import REGIONAL_AREA
from .models import Answer, Impact, Incident, IncidentWorkflow, SectorRegulation


# TO DO: change the templates to custom one
class ServicesListCheckboxSelectMultiple(ChoiceWidget):
    allow_multiple_selected = True
    input_type = "checkbox"
    template_name = "django/forms/widgets/service_checkbox_select.html"
    option_template_name = "django/forms/widgets/service_checkbox_option.html"
    add_id_index = False
    checked_attribute = {"checked": True}
    option_inherits_attrs = True
    initial_data = None

    def __init__(self, *args, **kwargs):
        if "initial" in kwargs:
            self.initial_data = kwargs.pop("initial")
        super().__init__(*args, **kwargs)

    def optgroups(self, name, value, attrs=None):
        """Return a list of optgroups for this widget."""
        groups = []
        has_selected = False

        for index, (option_value, option_label) in enumerate(self.choices):
            if option_value is None:
                option_value = ""
            subgroup = []
            if isinstance(option_label, (list, tuple)):
                group_name = option_value
                subindex = 0
                choices = option_label
            else:
                group_name = None
                subindex = None
                choices = [(option_value, option_label)]
            groups.append((group_name, subgroup, index))

            # other_choices = []
            for subvalue, sublabel in choices:
                selected = (not has_selected or self.allow_multiple_selected) and str(
                    subvalue
                ) in value
                has_selected |= selected
                # manage default value
                if self.initial_data is not None:
                    if subvalue in self.initial_data:
                        selected = True

                subgroup.append(
                    self.create_option(
                        name,
                        subvalue,
                        sublabel,
                        selected,
                        index,
                        subindex=subindex,
                        attrs=attrs,
                    )
                )

                if subindex is not None:
                    subindex += 1
        return groups


class DropdownCheckboxSelectMultiple(ChoiceWidget):
    allow_multiple_selected = True
    input_type = "select"
    template_name = "django/forms/widgets/dropdown_checkbox_select.html"
    option_template_name = "django/forms/widgets/dropdown_checkbox_option.html"
    option_inherits_attrs = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


# Class for Multichoice and single choice
# TO DO : improve layout
class OtherCheckboxSelectMultiple(ChoiceWidget):
    allow_multiple_selected = True
    input_type = "checkbox"
    template_name = "django/forms/widgets/other_checkbox_select.html"
    option_template_name = "django/forms/widgets/other_checkbox_option.html"

    def __init__(self, *args, **kwargs):
        if "input_type" in kwargs:
            self.input_type = kwargs.pop("input_type")
        super().__init__(*args, **kwargs)

    # this is the standard optgroups function, just add a hook to add new input
    # and modify the CSS class
    def optgroups(self, name, value, attrs=None):
        """Return a list of optgroups for this widget."""
        groups = []
        has_selected = False

        for index, (option_value, option_label) in enumerate(self.choices):
            if option_value is None:
                option_value = ""
            subgroup = []
            if isinstance(option_label, (list, tuple)):
                group_name = option_value
                subindex = 0
                choices = option_label
            else:
                group_name = None
                subindex = None
                choices = [(option_value, option_label)]
            groups.append((group_name, subgroup, index))

            # other_choices = []
            for subvalue, sublabel in choices:
                selected = (not has_selected or self.allow_multiple_selected) and str(
                    subvalue
                ) in value
                has_selected |= selected
                # add CSS class on the one who need additional answer
                # if sublabel.allowed_additional_answer:
                #     attrs["class"] = attrs["class"] + "need-additional-answer"
                subgroup.append(
                    self.create_option(
                        name,
                        subvalue,
                        sublabel,
                        selected,
                        index,
                        subindex=subindex,
                        attrs=attrs,
                    )
                )
                # if option_label.allowed_additional_answer:
                #     other_choices.append(sublabel)
                if subindex is not None:
                    subindex += 1
        return groups


class AuthenticationForm(OTPAuthenticationForm):
    otp_device = forms.CharField(required=False, widget=forms.HiddenInput)
    otp_challenge = forms.CharField(required=False, widget=forms.HiddenInput)


# create a form for each category and add fields which represent questions
class QuestionForm(forms.Form):
    # for dynamicly add question to forms
    def create_question(self, question_option, incident_workflow=None, incident=None):
        initial_data = None
        field_name = "__question__" + str(question_option.id)
        question = question_option.question
        question_type = question_option.question.question_type
        answer_queryset = Answer.objects.filter(
            question_options__question=question,
            incident_workflow=(
                incident.get_latest_incident_workflow()
                if incident
                else incident_workflow
            ),
        ).order_by("-timestamp")

        if question_type in ["MULTI", "MT", "SO", "ST"]:
            if answer_queryset.exists():
                initial_data = list(
                    answer_queryset.values_list("predefined_answers", flat=True)
                )

            choices = [
                (choice.id, choice)
                for choice in question.predefinedanswer_set.all().order_by("position")
            ]
            form_attrs = {
                "class": "form-check-input",
                "title": question.tooltip,
                "data-bs-toggle": "tooltip",
            }
            self.fields[field_name] = forms.MultipleChoiceField(
                required=question_option.is_mandatory,
                choices=choices,
                widget=(
                    forms.CheckboxSelectMultiple(attrs=form_attrs)
                    if question_type in ["MULTI", "MT"]
                    else OtherCheckboxSelectMultiple(
                        input_type="radio", attrs=form_attrs
                    )
                ),
                label=question.label,
                initial=initial_data,
            )

            if question_type in ["ST", "MT"]:
                value = str(answer_queryset.first()) if answer_queryset.exists() else ""
                self.fields[field_name + "_answer"] = forms.CharField(
                    required=question_option.is_mandatory,
                    widget=forms.TextInput(
                        attrs={
                            "class": "multichoice-input-freetext",
                            "value": value,
                            "title": question.tooltip,
                            "data-bs-toggle": "tooltip",
                        }
                    ),
                    label=_("Add details"),
                )
        elif question_type == "DATE":
            if answer_queryset.exists():
                answer = answer_queryset.first()
                initial_data = (
                    datetime.strptime(str(answer), "%Y-%m-%d %H:%M")
                    if str(answer) != ""
                    else None
                )

            self.fields[field_name] = forms.DateTimeField(
                widget=DateTimePickerInput(
                    options={
                        "maxDate": datetime.today().strftime("%Y-%m-%d 23:59:59"),
                    },
                    attrs={
                        "title": question.tooltip,
                        "data-bs-toggle": "tooltip",
                        "class": "empty_field" if not initial_data else "",
                    },
                ),
                required=question_option.is_mandatory,
                initial=initial_data,
                help_text=_("Date format yyyy-mm-dd hh:mm"),
            )
            self.fields[field_name].label = question.label
        elif question_type == "FREETEXT":
            if answer_queryset.exists():
                answer = answer_queryset.first()
                initial_data = str(answer) if str(answer) != "" else None

            self.fields[field_name] = forms.CharField(
                required=question_option.is_mandatory,
                widget=forms.Textarea(
                    attrs={
                        "rows": 3,
                        "title": question.tooltip,
                        "data-bs-toggle": "tooltip",
                        "class": "empty_field" if not initial_data else "",
                    }
                ),
                initial=str(initial_data or ""),
                label=question.label,
            )
        elif question_type in ["CL", "RL"]:
            if answer_queryset.exists():
                answer = answer_queryset.first()
                initial_data = list(filter(None, str(answer).split(",")))

            self.fields[field_name] = forms.MultipleChoiceField(
                required=question_option.is_mandatory,
                choices=countries if question_type == "CL" else REGIONAL_AREA,
                widget=DropdownCheckboxSelectMultiple(),
                label=question.label,
                initial=initial_data or [],
            )

    def __init__(self, *args, **kwargs):
        position = kwargs.pop("position", -1)
        workflow = kwargs.pop("workflow", None)
        incident_workflow = kwargs.pop("incident_workflow", None)
        incident = kwargs.pop("incident", None)
        super().__init__(*args, **kwargs)

        if incident_workflow:
            workflow = incident_workflow.workflow

        categories = (
            workflow.questionoptions_set.values_list("category_option", flat=True)
            .order_by("category_option__position")
            .distinct()
        )

        if position >= len(categories):
            raise ValueError("Position exceeds available categories.")

        category = categories[position]

        category_question_options = workflow.questionoptions_set.filter(
            category_option__id=category
        ).order_by("position")

        for question_option in category_question_options:
            self.create_question(question_option, incident_workflow, incident)


# the first question for preliminary notification
class ContactForm(forms.Form):
    company_name = forms.CharField(
        required=True,
        label=_("Name of the Operator"),
        max_length=100,
        widget=forms.TextInput(attrs={"class": "company_name"}),
    )

    contact_lastname = forms.CharField(
        required=True,
        max_length=100,
        widget=forms.TextInput(attrs={"class": "contact_lastname"}),
    )
    contact_firstname = forms.CharField(
        required=True,
        max_length=100,
        widget=forms.TextInput(attrs={"class": "contact_firstname"}),
    )
    contact_title = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={"class": "contact_title"}),
    )
    contact_email = forms.CharField(
        required=True,
        max_length=100,
        widget=forms.EmailInput(attrs={"class": "contact_email"}),
    )
    contact_telephone = forms.CharField(
        required=True,
        max_length=100,
        widget=forms.TextInput(attrs={"class": "contact_telephone"}),
    )

    is_technical_the_same = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "required checkbox ",
                "onclick": "if (checked==true) {"
                "document.getElementsByClassName('technical_lastname')[0].value="
                "document.getElementsByClassName('contact_lastname')[0].value; "
                "document.getElementsByClassName('technical_firstname')[0].value="
                "document.getElementsByClassName('contact_firstname')[0].value; "
                "document.getElementsByClassName('technical_title')[0].value="
                "document.getElementsByClassName('contact_title')[0].value; "
                "document.getElementsByClassName('technical_email')[0].value="
                "document.getElementsByClassName('contact_email')[0].value; "
                "document.getElementsByClassName('technical_telephone')[0].value="
                "document.getElementsByClassName('contact_telephone')[0].value;}",
            }
        ),
        initial=False,
    )
    technical_lastname = forms.CharField(
        required=True,
        max_length=100,
        widget=forms.TextInput(attrs={"class": "technical_lastname"}),
    )
    technical_firstname = forms.CharField(
        required=True,
        max_length=100,
        widget=forms.TextInput(attrs={"class": "technical_firstname"}),
    )
    technical_title = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={"class": "technical_title"}),
    )
    technical_email = forms.CharField(
        required=True,
        max_length=100,
        widget=forms.EmailInput(attrs={"class": "technical_email"}),
    )
    technical_telephone = forms.CharField(
        required=True,
        max_length=100,
        widget=forms.TextInput(attrs={"class": "technical_telephone"}),
    )

    incident_reference = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(
            attrs={
                "title": _(
                    "Please include a reference "
                    "(e.g., an identifier, internal reference, CERT reference, etc.) "
                    "to facilitate incident tracking."
                ),
                "data-bs-toggle": "tooltip",
            }
        ),
    )
    complaint_reference = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(
            attrs={
                "title": _(
                    "Insert the file number of a criminal complaint "
                    "that you have filed with the police."
                ),
                "data-bs-toggle": "tooltip",
            }
        ),
    )

    def prepare_initial_value(**kwargs):
        request = kwargs.pop("request")
        user = request.user
        if user.is_authenticated:
            company_name = (
                user.regulators.first()
                if is_user_regulator(user)
                else get_active_company_from_session(request)
            )
            return {
                "company_name": company_name,
                "contact_lastname": user.last_name,
                "contact_firstname": user.first_name,
                "contact_email": user.email,
                "contact_telephone": user.phone_number,
            }
        return {}


# prepare an array of sector and services
def construct_services_array(root_sectors):
    categs = dict()
    services = Service.objects.filter(
        Q(sector__in=root_sectors) | Q(sector__parent__in=root_sectors)
    )

    final_categs = []
    for service in services:
        if not categs.get(service.sector):
            categs[service.sector] = [[service.id, service]]
        else:
            categs[service.sector].append([service.id, service])

    for sector, list_of_options in categs.items():
        name = sector.name
        while sector.parent is not None:
            name = _(sector.parent.name) + " - " + _(name)
            sector = sector.parent
        final_categs.append([name, list_of_options])

    return final_categs


class RegulationForm(forms.Form):
    regulations = forms.MultipleChoiceField(
        required=True,
        widget=SortedCheckboxSelectMultiple(),
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
    regulations_id = (
        SectorRegulation.objects.filter(
            regulator__in=regulators, sectorregulationworkflow__isnull=False
        )
        .distinct("regulation__id")
        .values_list("regulation__id", flat=True)
    )

    regulations = (
        Regulation.objects.filter(id__in=regulations_id)
        .values_list("id", "translations__label")
        .distinct("id")
    )

    return regulations


class RegulatorForm(forms.Form):
    # generic impact definitions
    regulators = forms.MultipleChoiceField(
        required=True,
        choices=[],
        widget=SortedCheckboxSelectMultiple(),
        label=_("Send notification to"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.fields["regulators"].choices = [
                (
                    regulator.id,
                    f"{regulator.safe_translation_getter('name', any_language=True)} \
                    {regulator.safe_translation_getter('full_name', any_language=True)}",
                )
                for regulator in Regulator.objects.all()
                if regulator.sectorregulation_set.filter(
                    sectorregulationworkflow__isnull=False
                ).exists()
            ]
        except Exception:
            self.fields["regulators"].choices = []

    def get_selected_data(self):
        return self.fields["regulators"].initial


class DetectionDateForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Initialize the 'incident_timezone' field
        self.fields["incident_timezone"] = forms.ChoiceField(
            choices=[(tz, tz) for tz in pytz.common_timezones],
            widget=forms.Select(attrs={"class": "form-control"}),
            required=False,
            label=_("Select the incident time zone"),
            initial=kwargs.get("initial", {}).get("incident_timezone", None)
            or TIME_ZONE,
        )

        # Initialize the 'detection_date' field
        self.fields["detection_date"] = forms.DateTimeField(
            required=True,
            widget=DateTimePickerInput(
                options={
                    "maxDate": datetime.today().strftime("%Y-%m-%d 23:59"),
                },
            ),
            label=_("Select date and time"),
        )


class SectorForm(forms.Form):
    sectors = forms.MultipleChoiceField(
        required=True,
        widget=forms.CheckboxSelectMultiple(),
        label=_("Sectors"),
    )

    def __init__(self, *args, **kwargs):
        regulations = kwargs["initial"]["regulations"]
        regulators = kwargs["initial"]["regulators"]
        super().__init__(*args, **kwargs)

        self.fields["sectors"].choices = construct_sectors_array(
            regulations.all(), regulators.all()
        )

        if len(self.fields["sectors"].choices) == 0:
            self.fields["sectors"].required = False


def construct_sectors_array(regulations, regulators):
    sector_regulations = SectorRegulation.objects.filter(
        regulation__in=regulations, regulator__in=regulators
    )
    all_sectors = (
        Sector.objects.filter(sectorregulation__in=sector_regulations)
        .distinct()
        .order_by("parent")
    )

    categs = {}

    for sector in all_sectors:
        sector_name = sector.get_safe_translation()

        if sector.parent:
            parent_name = sector.parent.get_safe_translation()
            categs.setdefault(parent_name, []).append([sector.id, sector_name])
        else:
            if not categs.get(sector_name):
                categs.setdefault(sector_name, []).append([sector.id, sector_name])

    final_categs = [
        [sector, sorted(options, key=lambda item: item[1])]
        for sector, options in categs.items()
    ]

    return sorted(final_categs, key=lambda item: item[0])


def get_forms_list(incident=None, workflow=None, is_regulator=False):
    category_tree = []
    if incident is None:
        category_tree = [
            ContactForm,
            RegulatorForm,
            RegulationForm,
            SectorForm,
            DetectionDateForm,
        ]
    else:
        category_tree.append(IncidenteDateForm)
        if workflow is None:
            workflow = incident.get_next_step()
        categories = (
            workflow.questionoptions_set.filter(category_option__isnull=False)
            .values_list("category_option", flat=True)
            .distinct()
        )
        for _category in categories:
            category_tree.append(QuestionForm)
        if workflow.is_impact_needed:
            regulation_sector_has_impacts = Impact.objects.filter(
                regulation=incident.sector_regulation.regulation,
                sectors__in=incident.affected_sectors.all(),
            ).exists()
            if regulation_sector_has_impacts:
                category_tree.append(ImpactForm)
        if is_regulator:
            category_tree.append(RegulatorIncidentWorkflowCommentForm)
    return category_tree


class RegulatorIncidentEditForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = self.instance.id

    class Meta:
        model = Incident
        fields = [
            "id",
            "incident_id",
            "is_significative_impact",
            "review_status",
            "incident_status",
        ]


class RegulatorIncidentWorkflowCommentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = self.instance.id
        self.fields["comment"].widget.attrs.update(
            {
                "rows": 3,
                "class": "empty_field" if not self.initial["comment"] else "",
            }
        )

    class Meta:
        model = IncidentWorkflow
        fields = [
            "id",
            "comment",
            "review_status",
        ]


class ImpactForm(forms.Form):
    impacts = forms.MultipleChoiceField(
        required=False,
        widget=ServicesListCheckboxSelectMultiple(initial=None),
    )

    # prepare an array of impacts from incident sectorized
    def construct_impact_array(self, incident):
        impacts_array = []
        regulation = incident.sector_regulation.regulation
        for sector in incident.affected_sectors.all():
            subgroup = []
            if sector.impact_set.filter(regulation=regulation).count() > 0:
                for impact in sector.impact_set.filter(regulation=regulation):
                    subgroup.append([impact.id, str(impact)])
                impacts_array.append(
                    [
                        sector.get_safe_translation(),
                        sorted(subgroup, key=lambda item: item[1]),
                    ]
                )

        # Not needed anymore : just keep in case
        # impacts_without_sector = Impact.objects.all().filter(
        #     regulation=incident.sector_regulation.regulation, sectors=None
        # )
        # if impacts_without_sector.count() > 0:
        #     subgroup = []
        #     for impact in impacts_without_sector:
        #         subgroup.append([impact.id, impact.label])
        #     impacts_array.append(['others', subgroup])

        return impacts_array

    def __init__(self, *args, **kwargs):
        incident = None
        incident_workflow = None
        if "incident" in kwargs:
            incident = kwargs.pop("incident")
        if "incident_workflow" in kwargs:
            incident_workflow = kwargs.pop("incident_workflow")
        super().__init__(*args, **kwargs)

        if incident is not None:
            self.fields["impacts"].choices = self.construct_impact_array(incident)
        if incident_workflow is not None:
            # only with ServicesListCheckboxSelectMultiple
            self.fields["impacts"].widget.initial_data = [
                i.id for i in incident_workflow.impacts.all()
            ]
        else:
            previous_incident_workflow = incident.get_latest_incident_workflow()
            if previous_incident_workflow is not None:
                # only with ServicesListCheckboxSelectMultiple
                self.fields["impacts"].widget.initial_data = [
                    i.id for i in previous_incident_workflow.impacts.all()
                ]


# let the user change the date of his incident
class IncidenteDateForm(forms.ModelForm):
    incident_timezone = forms.ChoiceField(
        choices=[(tz, tz) for tz in pytz.common_timezones],
        widget=forms.Select(attrs={"class": "form-control"}),
        required=False,
        label=_("Select the incident time zone"),
        initial=TIME_ZONE,
    )

    incident_notification_date = forms.DateTimeField(
        widget=DateTimePickerInput(),
        required=False,
    )

    incident_detection_date = forms.DateTimeField(
        widget=DateTimePickerInput(
            options={}, attrs={"class": "incident_detection_date"}
        ),
        required=False,
        help_text=_("Date format yyyy-mm-dd hh:mm"),
    )

    incident_starting_date = forms.DateTimeField(
        widget=DateTimePickerInput(
            options={}, attrs={"class": "incident_starting_date"}
        ),
        required=False,
        help_text=_("Date format yyyy-mm-dd hh:mm"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.incident = self.instance

        self.fields["incident_notification_date"].disabled = True

        if self.incident:
            i_timezone = (
                self.incident.incident_timezone
                if self.incident.incident_timezone
                else TIME_ZONE
            )
            i_notification_date = (
                self.incident.incident_notification_date
                if self.incident.incident_notification_date
                else None
            )

            i_detection_date = (
                self.incident.incident_detection_date
                if self.incident.incident_detection_date
                else None
            )
            timezone = pytz.timezone(i_timezone)

            if i_notification_date:
                maxDate_notification = format_datetime_astimezone(
                    i_notification_date, timezone
                )
                self.fields["incident_detection_date"].widget.config.options[
                    "maxDate"
                ] = maxDate_notification

                self.fields["incident_starting_date"].widget.config.options[
                    "maxDate"
                ] = maxDate_notification

            if self.incident.sector_regulation.is_detection_date_needed:
                maxDate_detection = format_datetime_astimezone(
                    i_detection_date, timezone
                )

                self.fields["incident_starting_date"].widget.config.options[
                    "maxDate"
                ] = maxDate_detection
                self.fields["incident_detection_date"].disabled = True
                self.fields["incident_timezone"].disabled = True

            if i_timezone != TIME_ZONE:
                self.fields["incident_timezone"].disabled = True

            set_initial_datetime(
                self,
                "incident_notification_date",
                i_notification_date,
                timezone,
            )

            set_initial_datetime(
                self,
                "incident_detection_date",
                i_detection_date,
                timezone,
            )
            set_initial_datetime(
                self,
                "incident_starting_date",
                self.incident.incident_starting_date,
                timezone,
            )

    class Meta:
        model = Incident
        fields = [
            "id",
            "incident_timezone",
            "incident_notification_date",
            "incident_detection_date",
            "incident_starting_date",
        ]


class IncidentWorkflowForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["review_status"].required = False
        self.fields["review_status"].widget.attrs = {
            "class": "border-0 form-select-sm py-0 select-break-spaces",
            "onchange": f"onChangeWorkflowStatus(this, {self.instance.incident_id}, {self.instance.pk})",
        }

    class Meta:
        model = IncidentWorkflow
        fields = ["review_status"]


class IncidentStatusForm(forms.ModelForm):
    def clean(self):
        cleaned_data = super().clean()
        # prevent is_significative_impact to go FALSE when we change an other field
        if len(cleaned_data) > 1:
            cleaned_data[
                "is_significative_impact"
            ] = self.instance.is_significative_impact
        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        onchange_funtion = f"onChangeIncident(this, {self.instance.pk})"
        classes_select_widget = "border-0 form-select-sm py-0 select-break-spaces"

        self.fields["incident_id"].widget.attrs = {
            "class": "form-control-sm",
            "onchange": onchange_funtion,
        }
        self.fields["incident_status"].widget.attrs = {
            "class": classes_select_widget,
            "onchange": onchange_funtion,
        }
        self.fields["review_status"].widget.attrs = {
            "class": classes_select_widget,
            "onchange": onchange_funtion,
        }

        self.fields["is_significative_impact"].widget.attrs = {
            "class": "large-checkbox",
            "onchange": onchange_funtion,
        }

    class Meta:
        model = Incident
        fields = [
            "incident_id",
            "review_status",
            "incident_status",
            "is_significative_impact",
        ]

        required = {
            "incident_id": False,
            "review_status": False,
            "incident_status": False,
            "is_significative_impact": False,
        }


def format_datetime_astimezone(datetime, timezone):
    return datetime.astimezone(timezone).strftime("%Y-%m-%d %H:%M")


def set_initial_datetime(form, field_name, datetime_value, timezone):
    if datetime_value:
        form.initial[field_name] = format_datetime_astimezone(datetime_value, timezone)
    else:
        form.fields[field_name].widget.attrs["class"] = (
            form.fields[field_name].widget.attrs.get("class", "") + " empty_field"
        )

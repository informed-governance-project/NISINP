from datetime import datetime
from functools import partial
from operator import is_not

from bootstrap_datepicker_plus.widgets import DatePickerInput
from django import forms
from django.db.models import Q
from django.forms.widgets import ChoiceWidget
from django.utils.translation import gettext as _
from django_countries import countries
from django_otp.forms import OTPAuthenticationForm

from governanceplatform.models import Regulator, Service, Regulation

from .globals import REGIONAL_AREA
from .models import Answer, Incident, Question, QuestionCategory, Reglementation


# TO DO: change the templates to custom one
class ServicesListCheckboxSelectMultiple(ChoiceWidget):
    allow_multiple_selected = True
    input_type = "checkbox"
    template_name = "django/forms/widgets/service_checkbox_select.html"
    option_template_name = "django/forms/widgets/service_checkbox_option.html"
    add_id_index = False
    checked_attribute = {"selected": True}
    option_inherits_attrs = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


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
    label = forms.CharField(widget=forms.HiddenInput(), required=False)

    # for dynamicly add question to forms
    def create_question(self, question, incident=None):
        initial_data = []
        if (
            question.question_type == "MULTI"
            or question.question_type == "MT"
            or question.question_type == "SO"
            or question.question_type == "ST"
        ):
            initial_answer = ""
            input_type = "checkbox"
            choices = []
            if question.question_type == "SO" or question.question_type == "ST":
                input_type = "radio"
            if incident is not None:
                initial_data = list(
                    filter(
                        partial(is_not, None),
                        Answer.objects.values_list("predefined_answers", flat=True)
                        .filter(question=question, incident=incident)
                        .order_by("position"),
                    )
                )
            for choice in question.predefined_answers.all().order_by("position"):
                choices.append([choice.id, choice])
            self.fields[str(question.id)] = forms.MultipleChoiceField(
                required=question.is_mandatory,
                choices=choices,
                widget=OtherCheckboxSelectMultiple(
                    input_type=input_type,
                    attrs={
                        "title": question.tooltip,
                        "data-bs-toggle": "tooltip",
                    },
                ),
                label=question.label,
                initial=initial_data,
            )
            if question.question_type == "MT" or question.question_type == "ST":
                answer = Answer.objects.values_list("answer", flat=True).filter(
                    question=question, incident=incident
                )
                if len(answer) > 0:
                    if answer[0] != "":
                        initial_answer = list(filter(partial(is_not, ""), answer))[0]
                self.fields[str(question.id) + "_answer"] = forms.CharField(
                    required=True,
                    widget=forms.TextInput(
                        attrs={
                            "class": "multichoice-input-freetext",
                            "value": str(initial_answer),
                            "title": question.tooltip,
                            "data-bs-toggle": "tooltip",
                        }
                    ),
                    label="Add precision",
                )
        elif question.question_type == "DATE":
            initial_data = ""
            if incident is not None:
                answer = Answer.objects.values_list("answer", flat=True).filter(
                    question=question, incident=incident
                )
                if answer.count() > 0:
                    if answer[0] != "":
                        initial_data = list(filter(partial(is_not, ""), answer))[0]
                        initial_data = datetime.strptime(
                            initial_data, "%Y-%m-%d %H:%m:%s"
                        ).date()
            self.fields[str(question.id)] = forms.DateField(
                widget=DatePickerInput(
                    options={
                        "format": "YYYY-MM-DD HH:mm:ss",
                        "maxDate": datetime.today().strftime("%Y-%m-%d 23:59:59"),
                    },
                    attrs={
                        "title": question.tooltip,
                        "data-bs-toggle": "tooltip",
                    },
                ),
                required=question.is_mandatory,
                initial=initial_data,
            )
            self.fields[str(question.id)].label = question.label
        elif question.question_type == "FREETEXT":
            initial_data = ""
            if incident is not None:
                answer = Answer.objects.values_list("answer", flat=True).filter(
                    question=question, incident=incident
                )
                if len(answer) > 0:
                    if answer[0] != "":
                        initial_data = list(filter(partial(is_not, ""), answer))[0]
            self.fields[str(question.id)] = forms.CharField(
                required=question.is_mandatory,
                widget=forms.Textarea(
                    attrs={
                        "value": str(initial_data),
                        "title": question.tooltip,
                        "data-bs-toggle": "tooltip",
                    }
                ),
                label=question.label,
            )
        elif question.question_type == "CL" or question.question_type == "RL":
            initial_data = ""
            if incident is not None:
                answer = Answer.objects.values_list("answer", flat=True).filter(
                    question=question, incident=incident
                )
                if len(answer) > 0:
                    if answer[0] != "":
                        initial_data = list(filter(partial(is_not, ""), answer))[0]
            initial_data = list(initial_data.split(","))
            if question.question_type == "CL":
                choices = countries
            else:
                choices = REGIONAL_AREA
            self.fields[str(question.id)] = forms.MultipleChoiceField(
                choices=choices,
                widget=DropdownCheckboxSelectMultiple(),
                label=question.label,
                initial=initial_data,
            )

    def __init__(self, *args, **kwargs):
        position = -1
        if "position" in kwargs:
            position = kwargs.pop("position")
        if "incident" in kwargs:
            incident = kwargs.pop("incident")
        else:
            incident = None
        if "is_preliminary" in kwargs:
            is_preliminary = kwargs.pop("is_preliminary")
        else:
            is_preliminary = True
        super().__init__(*args, **kwargs)

        if position > -1:
            categories = (
                QuestionCategory.objects.all()
                .order_by("position")
                .filter(question__is_preliminary=is_preliminary)
                .distinct()
            )
            category = categories[position]
            questions = (
                Question.objects.all()
                .filter(category=category, is_preliminary=is_preliminary)
                .order_by("position")
            )
            for question in questions:
                self.create_question(question, incident)


# the first question for preliminary notification
class ContactForm(forms.Form):
    company_name = forms.CharField(required=True, label="Company name", max_length=100)

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
                    "Insert a reference to find and track easily your incident (internal reference, CERT reference, etc.)"
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
                "title": _("Insert any complaint has been filed with the police"),
                "data-bs-toggle": "tooltip",
            }
        ),
    )

    def prepare_initial_value(**kwargs):
        request = kwargs.pop("request")
        if request.user.is_authenticated:
            return {
                "contact_lastname": request.user.last_name,
                "contact_firstname": request.user.first_name,
                "contact_email": request.user.email,
                "contact_telephone": request.user.phone_number,
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
        widget=forms.CheckboxSelectMultiple(attrs={"class": "multiple-selection"}),
    )

    def __init__(self, *args, **kwargs):
        regulators = kwargs['initial']['regulators']
        super().__init__(*args, **kwargs)

        self.fields["regulations"].choices = construct_regulation_array(
            regulators.all()
        )


# prepare an array of regulations
def construct_regulation_array(regulators):
    regulations_to_select = []
    regulations = Regulation.objects.all()

    for regulation in regulations:
        for regulator in regulators:
            if regulator in regulation.regulators.all():
                regulations_to_select.append([regulation.id, regulation.label])

    return regulations_to_select


class RegulatorForm(forms.Form):
    initial_data = [
        (k.id, k.name)
        for k in Regulator.objects.all()
    ]

    # generic impact definitions
    regulators = forms.MultipleChoiceField(
        required=True,
        choices=initial_data,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "multiple-selection"}),
        label="Send notification to:",
    )


class SectorForm(forms.Form):
    sectors = forms.MultipleChoiceField(
        required=True,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "multiple-selection"}),
    )

    def __init__(self, *args, **kwargs):
        regulations = kwargs['initial']['regulations']
        regulators = kwargs['initial']['regulators']
        super().__init__(*args, **kwargs)

        self.fields["sectors"].choices = construct_sectors_array(
            regulations.all(), regulators.all()
        )


# prepare an array of sectors
def construct_sectors_array(regulations, regulators):
    sectors_to_select = []
    reglementations = Reglementation.objects.all().filter(
        regulation__in=regulations,
        regulator__in=regulators
    )

    for reglementation in reglementations:
        for sector in reglementation.sectors.all():
            sectors_to_select.append([sector.id, sector.name])

    return sectors_to_select


def get_forms_list(is_preliminary=True):
    categories = (
        QuestionCategory.objects.all()
        .filter(question__is_preliminary=is_preliminary)
        .distinct()
    )

    if is_preliminary is True:
        category_tree = [
            ContactForm,
            RegulatorForm,
            RegulationForm,
            SectorForm,
        ]

    for _category in categories:
        category_tree.append(QuestionForm)

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

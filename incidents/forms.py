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

from governanceplatform.models import Company, Service

from .globals import REGIONAL_AREA
from .models import Answer, Impact, Incident, Question, QuestionCategory, RegulationType


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
                        Answer.objects.values_list(
                            "predefined_answers", flat=True
                        ).filter(question=question, incident=incident),
                    )
                )
            for choice in question.predefined_answers.all():
                choices.append([choice.id, choice])
            self.fields[str(question.id)] = forms.MultipleChoiceField(
                required=question.is_mandatory,
                choices=choices,
                widget=OtherCheckboxSelectMultiple(
                    input_type=input_type,
                    # attrs={"class": "multiple-selection"}
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
                    required=False,
                    widget=forms.TextInput(
                        attrs={
                            "class": "multichoice-input-freetext",
                            "value": str(initial_answer),
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
                    }
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
                widget=forms.Textarea(attrs={"value": str(initial_data)}),
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
    company_name = forms.CharField(label="Company name", max_length=100)

    contact_lastname = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={"class": "contact_lastname"}),
    )
    contact_firstname = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={"class": "contact_firstname"}),
    )
    contact_title = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={"class": "contact_title"}),
    )
    contact_email = forms.CharField(
        max_length=100,
        widget=forms.EmailInput(attrs={"class": "contact_email"}),
    )
    contact_telephone = forms.CharField(
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
        max_length=100,
        widget=forms.TextInput(attrs={"class": "technical_lastname"}),
    )
    technical_firstname = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={"class": "technical_firstname"}),
    )
    technical_title = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={"class": "technical_title"}),
    )
    technical_email = forms.CharField(
        max_length=100,
        widget=forms.EmailInput(attrs={"class": "technical_email"}),
    )
    technical_telephone = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={"class": "technical_telephone"}),
    )

    incident_reference = forms.CharField(max_length=255, required=False)
    complaint_reference = forms.CharField(max_length=255, required=False)

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


# the affected services with services load from services table
class ImpactedServicesForm(forms.Form):
    regulationTypes = RegulationType.objects.all()

    choices_rt = []
    for choice in regulationTypes:
        choices_rt.append([choice.id, choice])

    regulation = forms.MultipleChoiceField(
        required=False,
        choices=choices_rt,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "multiple-selection"}),
    )
    affected_services = forms.MultipleChoiceField(
        required=False,
        widget=DropdownCheckboxSelectMultiple(attrs={"class": "multiple-selection"}),
    )

    def __init__(self, *args, **kwargs):
        sectors = kwargs.pop("sectors", None)
        super().__init__(*args, **kwargs)

        self.fields["affected_services"].choices = construct_services_array(
            sectors.all()
        )


class ImpactForFinalNotificationForm(forms.Form):
    # list of impact present in the incident table
    initial_data = []
    # generic impact definitions
    generic_impact = forms.MultipleChoiceField(
        required=False,
        choices=[],
        widget=forms.CheckboxSelectMultiple(attrs={"class": "multiple-selection"}),
        label="Generic impacts",
    )

    # create the questions for the impacted sectors
    def create_questions(self, affected_services, initial_data=None):
        if not initial_data:
            initial_data = []
        sectors = []
        for service in affected_services:
            sectors.append(service.sector)
            for sector in sectors:
                choices = [(k.id, k.label) for k in sector.specific_impact.all()]
                self.fields[str(sector.id)] = forms.MultipleChoiceField(
                    required=False,
                    choices=choices,
                    widget=forms.CheckboxSelectMultiple(
                        attrs={"class": "multiple-selection"}
                    ),
                    label=sector.name,
                    initial=initial_data,
                )

    def __init__(self, *args, **kwargs):
        if "incident" in kwargs:
            incident = kwargs.pop("incident")
            # get initial data if there are existing
            if incident is not None:
                initial_data = list(incident.impacts.values_list("id", flat=True))
            affected_services = incident.affected_services.all()
            super().__init__(*args, **kwargs)
            self.create_questions(affected_services, initial_data)
        else:
            super().__init__(*args, **kwargs)
        # init the generic choices
        self.fields["generic_impact"].choices = [
            (k.id, k.label) for k in Impact.objects.all().filter(is_generic_impact=True)
        ]
        self.fields["generic_impact"].initial = initial_data


def get_forms_list(is_preliminary=True):
    categories = (
        QuestionCategory.objects.all()
        .filter(question__is_preliminary=is_preliminary)
        .distinct()
    )

    if is_preliminary is True:
        category_tree = [
            ContactForm,
            ImpactedServicesForm,
            NotificationDispatchingForm,
        ]
    else:
        category_tree = [ImpactForFinalNotificationForm]

    for _category in categories:
        category_tree.append(QuestionForm)

    return category_tree


class NotificationDispatchingForm(forms.Form):
    initial_data = [
        (k.id, k.name + " " + k.full_name + " " + k.description)
        for k in Company.objects.all().filter(
            is_regulator=True,
        )
    ]

    # generic impact definitions
    authorities_list = forms.MultipleChoiceField(
        required=True,
        choices=initial_data,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "multiple-selection"}),
        label="Send notification to:",
    )

    other_authority = forms.CharField(
        required=False,
        widget=forms.EmailInput(attrs={"placeholder": "other_authority@exemple.com"}),
        label="Send to another authority:",
    )


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

from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.forms import formset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils.translation import gettext as _
from formtools.wizard.views import SessionWizardView

from governanceplatform.models import Service
from governanceplatform.settings import (
    EMAIL_SENDER,
    MAX_PRELIMINARY_NOTIFICATION_PER_DAY_PER_USER,
    SITE_NAME,
)

from .forms import (
    ContactForm,
    ImpactForFinalNotificationForm,
    QuestionForm,
    RegulatorIncidentForm,
    get_number_of_question,
)
from .models import (
    Answer,
    Email,
    Incident,
    PredifinedAnswer,
    Question,
    QuestionCategory,
)

# TODO : put the correct decorator


@login_required
def get_incidents(request):
    """Returns the list of incidents."""
    user = request.user
    incidents = (
        Incident.objects.all()
        .order_by("preliminary_notification_date")
        .filter(contact_user=user)
    )
    return render(
        request,
        "incidents.html",
        context={"site_name": SITE_NAME, "incidents": incidents},
    )


@login_required
def get_form_list(request, form_list=None):
    if is_incidents_report_limit_reached(request):
        return HttpResponseRedirect("/incidents")
    """Initialize data for the preliminary notification."""
    if form_list is None:
        form_list = get_number_of_question()
    return FormWizardView.as_view(
        form_list,
        initial_dict={"0": ContactForm.prepare_initial_value(request=request)},
    )(request)


@login_required
def get_final_notification_list(request, form_list=None, pk=None):
    if form_list is None:
        form_list = get_number_of_question(is_preliminary=False)
    if pk is not None:
        request.incident = pk
    return FinalNotificationWizardView.as_view(
        form_list,
    )(request)


@login_required
def get_incidents_for_regulator(request):
    """Returns the list of incident as regulator."""
    incidents = (
        Incident.objects.all()
        .order_by("preliminary_notification_date")
        .values(
            "id",
            "regulations",
            "incident_id",
            "affected_services",
            "is_significative_impact",
            "preliminary_notification_date",
            "final_notification_date",
        )
    )
    paginator = Paginator(incidents, 10)  # Show 10 incident per page.
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    incident_formset = formset_factory(RegulatorIncidentForm, extra=0)
    formset = incident_formset(initial=page_obj)
    return render(
        request,
        "regulator/incidents.html",
        context={
            "site_name": SITE_NAME,
            "incidents": incidents,
            "forms": formset,
            "page_obj": page_obj,
        },
    )


def is_incidents_report_limit_reached(request):
    if request.user.is_authenticated:
        user = request.user
        # if a user make too many declaration we prevent to save
        number_preliminary_today = Incident.objects.filter(
            contact_user=user, preliminary_notification_date=date.today()
        ).count()
        if number_preliminary_today >= MAX_PRELIMINARY_NOTIFICATION_PER_DAY_PER_USER:
            messages.add_message(
                request,
                messages.WARNING,
                "The incidents reports per day have been reached. Try again tomorrow.",
            )
            return True
    return False


class FormWizardView(SessionWizardView):
    """Wizard to manage the preliminary form."""

    template_name = "declaration.html"

    def __init__(self, **kwargs):
        self.form_list = kwargs.pop("form_list")
        self.initial_dict = kwargs.pop("initial_dict")
        return super().__init__(**kwargs)

    def get_form(self, step=None, data=None, files=None):
        if step is None:
            step = self.steps.current
        position = int(step)
        # when we have passed the fixed forms
        if position > 2:
            # create the form with the correct question/answers
            form = QuestionForm(data, position=position - 3)

            return form
        else:
            form = super().get_form(step, data, files)
        return form

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)

        categories = (
            QuestionCategory.objects.filter(question__is_preliminary=True)
            .order_by("position")
            .distinct()
        )

        context["steps"] = [
            _("Contact"),
            _("Impacted Services"),
            _("Notification Dispatching"),
        ]

        for categorie in categories:
            context["steps"].append(categorie.label)

        return context

    def done(self, form_list, **kwargs):
        if is_incidents_report_limit_reached(self.request):
            return HttpResponseRedirect("/incidents")

        data = [form.cleaned_data for form in form_list]
        user = self.request.user
        # TO DO : Take the company from the selection module
        company = None

        incident = Incident.objects.create(
            contact_lastname=data[0]["contact_lastname"],
            contact_firstname=data[0]["contact_firstname"],
            contact_title=data[0]["contact_title"],
            contact_email=data[0]["contact_email"],
            contact_telephone=data[0]["contact_telephone"],
            # technical contact
            technical_lastname=data[0]["technical_lastname"],
            technical_firstname=data[0]["technical_firstname"],
            technical_title=data[0]["technical_title"],
            technical_email=data[0]["technical_email"],
            technical_telephone=data[0]["technical_telephone"],
            incident_reference=data[0]["incident_reference"],
            complaint_reference=data[0]["complaint_reference"],
            contact_user=user,
            company=company,
            company_name=company.name
            if company is not None
            else data[0]["company_name"],
        )
        for regulation in data[1]["regulation"]:
            incident.regulations.add(regulation)

        # incident reference
        company_for_ref = ""
        sector_for_ref = ""
        subsector_for_ref = ""
        if company is None:
            company_for_ref = data[0]["company_name"][:4]

        for service in data[1]["affected_services"]:
            try:
                service = int(service)
                incident.affected_services.add(service)
                if subsector_for_ref == "":
                    service_entity = Service.objects.get(id=service)
                    sector = service_entity.sector
                    subsector_for_ref = sector.accronym[:3]
                    if sector.parent is not None:
                        sector_for_ref = sector.parent.accronym[:3]
            except Exception:
                pass

        # TO DO : improve with proy and company
        if company is None:
            int_id = 0
            ids = Incident.objects.filter(
                incident_id__icontains=company_for_ref
            ).values_list("incident_id", flat=True)
            for id in ids:
                id = int(id[-9:-5])
                if id > int_id:
                    int_id = id
            int_id = int_id + 1
        number_of_incident = f"{int_id:04}"
        incident.incident_id = (
            company_for_ref
            + "_"
            + sector_for_ref
            + "_"
            + subsector_for_ref
            + "_"
            + number_of_incident
            + "_"
            + str(date.today().year)
        )
        incident.save()

        # save questions
        saveAnswers(3, data, incident)

        # Send Email
        email = Email.objects.filter(email_type="PRELI").first()
        if email is not None:
            send_mail(
                email.subject,
                email.content,
                EMAIL_SENDER,
                [user.email],
                fail_silently=True,
            )
        return HttpResponseRedirect("/incidents")


class FinalNotificationWizardView(SessionWizardView):
    """Wizard to manage the final notification form."""

    template_name = "declaration.html"
    incident = None

    def __init__(self, **kwargs):
        self.form_list = kwargs.pop("form_list")
        return super().__init__(**kwargs)

    def get_form(self, step=None, data=None, files=None):
        if self.request.incident:
            self.incident = Incident.objects.get(pk=self.request.incident)
        if step is None:
            step = self.steps.current
        position = int(step)
        # when we have passed the fixed forms
        if position == 0:
            # create the form with the correct question/answers
            form = ImpactForFinalNotificationForm(data, incident=self.incident)

            return form

        elif position > 0:
            form = QuestionForm(
                data,
                position=position - 1,
                is_preliminary=False,
                incident=self.incident,
            )

        else:
            form = super().get_form(step, data, files)
        return form

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)

        categories = (
            QuestionCategory.objects.filter(question__is_preliminary=False)
            .order_by("position")
            .distinct()
        )

        context["steps"] = [_("Impacts")]

        for categorie in categories:
            context["steps"].append(categorie.label)

        return context

    def done(self, form_list, **kwargs):
        data = [form.cleaned_data for form in form_list]
        if self.incident is None:
            self.incident = Incident.objects.get(pk=self.request.incident)

        # manage impacts
        self.incident.is_significative_impact = False
        self.incident.impacts.set([])
        for _key, values in data[0].items():
            for v in values:
                # if we go there some values have been ticked so the impact is significative
                self.incident.is_significative_impact = True
                self.incident.impacts.add(int(v))

        # get the email type
        email = None
        if self.incident.final_notification_date is None:
            email = Email.objects.filter(email_type="FINAL").first()
        else:
            email = Email.objects.filter(email_type="ADD").first()

        self.incident.final_notification_date = date.today()
        self.incident.save()
        # manage question
        saveAnswers(1, data, self.incident)
        if email is not None:
            send_mail(
                email.subject,
                email.content,
                EMAIL_SENDER,
                [self.incident.contact_user.email],
                fail_silently=True,
            )
        return HttpResponseRedirect("/incidents")


def saveAnswers(index=0, data=None, incident=None):
    """Save the answers."""
    predifinedAnswers = []
    for d in range(index, len(data)):
        for key, value in data[d].items():
            question_id = None
            try:
                question_id = int(key)
            except Exception:
                pass
            if question_id is not None:
                question = Question.objects.get(pk=key)
                # we delete the previous answer in case we are doing an additional notification
                if incident is not None:
                    Answer.objects.filter(question=question, incident=incident).delete()
                if question.question_type == "FREETEXT":
                    answer = value
                elif question.question_type == "DATE":
                    if value is not None:
                        answer = value.strftime("%m/%d/%Y %H:%M:%S")
                    else:
                        answer = None
                elif question.question_type == "CL" or question.question_type == "RL":
                    answer = ""
                    for val in value:
                        answer += val + ","
                    answer = answer
                else:  # MULTI
                    predifinedAnswers = []
                    for val in value:
                        predifinedAnswer = PredifinedAnswer.objects.get(pk=val)
                        predifinedAnswers.append(predifinedAnswer)
                    answer = None
                    if data[d].get(key + "_answer"):
                        answer = data[d][key + "_answer"]
                answer_object = Answer.objects.create(
                    incident=incident,
                    question=question,
                    answer=answer,
                )
                answer_object.PredifinedAnswer.set(predifinedAnswers)

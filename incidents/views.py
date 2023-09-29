from datetime import date
from urllib.parse import urlparse

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.utils.translation import gettext as _
from formtools.wizard.views import SessionWizardView

from governanceplatform.helpers import (
    get_company_session,
    is_user_regulator,
    user_in_group
)
from governanceplatform.models import Service
from governanceplatform.settings import (
    EMAIL_SENDER,
    MAX_PRELIMINARY_NOTIFICATION_PER_DAY_PER_USER,
    PUBLIC_URL,
    SITE_NAME,
)

from .decorators import regulator_role_required
from .forms import (
    ContactForm,
    ImpactedServicesForm,
    ImpactForFinalNotificationForm,
    QuestionForm,
    RegulatorIncidentEditForm,
    get_forms_list,
)
from .models import (
    Answer,
    Email,
    Incident,
    PredefinedAnswer,
    Question,
    QuestionCategory,
)
from .pdf_generation import get_pdf_report
from .email import (replace_email_variables)


@login_required
def get_incidents(request):
    """Returns the list of incidents depending on the account type."""
    company_in_use = request.session.get("company_in_use")
    incidents = Incident.objects.order_by("-preliminary_notification_date")

    # RegulatorAdmin can see all the incidents reported by operators.
    if not user_in_group(request.user, "RegulatorAdmin"):
        # RegulatorUser has access to all incidents linked by sectors.
        if user_in_group(request.user, "RegulatorStaff"):
            incidents = incidents.filter(affected_services__sector__in=request.user.sectors.all())
        else:
            incidents = incidents.filter(
                company__id=company_in_use
            ) if company_in_use else incidents.filter(contact_user=request.user)

    if request.GET.get("incidentId"):
        incidents = incidents.filter(incident_id__icontains=request.GET.get("incidentId"))

    # Show 20 incidents per page.
    paginator = Paginator(incidents, 20)
    page_number = request.GET.get("page")
    incidents_page = paginator.get_page(page_number)

    # add paggination to the regular incidents view.
    return render(
        request,
        "regulator/incidents.html" if is_user_regulator(request.user) else "incidents.html",
        context={
            "site_name": SITE_NAME,
            "incidents": incidents,
            "incidents_page": incidents_page,
        },
    )


@login_required
def get_form_list(request, form_list=None):
    if is_incidents_report_limit_reached(request):
        return HttpResponseRedirect("/incidents")
    """Initialize data for the preliminary notification."""
    if form_list is None:
        form_list = get_forms_list()
    return FormWizardView.as_view(
        form_list,
        initial_dict={"0": ContactForm.prepare_initial_value(request=request)},
    )(request)


@login_required
def get_final_notification_list(request, form_list=None, incident_id=None):
    if form_list is None:
        form_list = get_forms_list(is_preliminary=False)
    if incident_id is not None:
        request.incident = incident_id
    return FinalNotificationWizardView.as_view(
        form_list,
    )(request)


@login_required
@regulator_role_required
def get_regulator_incident_edit_form(request, incident_id: int):
    """Returns the list of incident as regulator."""
    incident = Incident.objects.get(pk=incident_id)
    regulator_incident_form = RegulatorIncidentEditForm(
        instance=incident, data=request.POST if request.method == "POST" else None
    )

    if request.method == "POST":
        if regulator_incident_form.is_valid():
            regulator_incident_form.save()
            messages.success(
                request,
                f"Incident {incident.incident_id} has been successfully saved.",
            )
            response = HttpResponseRedirect(request.session.get("return_page", "/incidents"))
            try:
                del request.session["return_page"]
            except KeyError:
                pass

            return response

    if not request.session.get("return_page"):
        request.session["return_page"] = request.headers.get("referer", "/incidents")

    return render(
        request,
        "regulator/incident_edit.html",
        context={
            "regulator_incident_form": regulator_incident_form,
            "incident": incident,
        },
    )


@login_required
def download_incident_pdf(request, incident_id: int):
    target = request.headers.get("referer", "/")
    if not can_redirect(target):
        target = "/"

    # TODO: check for the permissions depending on the user type. RegulatorsUser by sector
    # OperatorUser or OperatorAdmin check company.
    try:
        pdf_report = get_pdf_report(incident_id, request)
    except Exception:
        messages.warning(request, "An error occurred when generating the report.")
        return HttpResponseRedirect(target)

    response = HttpResponse(pdf_report, content_type="application/pdf")
    response["Content-Disposition"] = "attachment;filename=Incident_{}_{}.pdf".format(
        incident_id, date.today()
    )

    return response


def is_incidents_report_limit_reached(request):
    if request.user.is_authenticated:
        user = request.user
        # if a user make too many declaration we prevent to save
        number_preliminary_today = Incident.objects.filter(
            contact_user=user, preliminary_notification_date=date.today()
        ).count()
        if number_preliminary_today >= MAX_PRELIMINARY_NOTIFICATION_PER_DAY_PER_USER:
            messages.warning(
                request,
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
        company_in_use = get_company_session(self.request)
        if step is None:
            step = self.steps.current
        position = int(step)
        # when we have passed the fixed forms
        if position == 1:
            form = ImpactedServicesForm(data, sectors=company_in_use.sectors)

            return form
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

        # notification dispatching
        for authority in data[2]["authorities_list"]:
            authority = int(authority)
            incident.authorities.add(authority)
        incident.other_authority = data[2]["other_authority"]
        incident.save()

        # save questions
        save_answers(3, data, incident)

        # Send Email
        email = Email.objects.filter(email_type="PRELI").first()
        if email is not None:
            send_mail(
                replace_email_variables(email.subject, incident),
                replace_email_variables(email.content, incident),
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
        save_answers(1, data, self.incident)
        if email is not None:
            send_mail(
                replace_email_variables(email.subject, self.incident),
                replace_email_variables(email.content, self.incident),
                EMAIL_SENDER,
                [self.incident.contact_user.email],
                fail_silently=True,
            )
        return HttpResponseRedirect("/incidents")


def save_answers(index=0, data=None, incident=None):
    """Save the answers."""
    for d in range(index, len(data)):
        for key, value in data[d].items():
            question_id = None
            try:
                question_id = int(key)
            except Exception:
                pass
            if question_id is not None:
                predefined_answers = []
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
                    for val in value:
                        predefined_answers.append(PredefinedAnswer.objects.get(pk=val))
                    answer = None
                    if data[d].get(key + "_answer"):
                        answer = data[d][key + "_answer"]
                answer_object = Answer.objects.create(
                    incident=incident,
                    question=question,
                    answer=answer,
                )
                answer_object.predefined_answers.set(predefined_answers)


def can_redirect(url: str) -> bool:
    """
    Check if a redirect is authorised.
    """
    o = urlparse(url)
    return o.netloc in PUBLIC_URL

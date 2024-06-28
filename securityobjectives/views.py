from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django_otp.decorators import otp_required
from django.utils.translation import gettext as _
from django.contrib import messages
from django.http import HttpResponseRedirect

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from formtools.wizard.views import SessionWizardView
from governanceplatform.helpers import (
    is_user_regulator,
    get_active_company_from_session,
)
from .filters import StandardAnswerFilter
from governanceplatform.settings import (
    SITE_NAME,
)

from .models import (
    StandardAnswer,
    Standard,
)
from .forms import (
    get_forms_list,
)
from governanceplatform.models import Regulator, Regulation


@login_required
@otp_required
def get_security_objectives(request):
    """Returns the list of SecurityObjectives"""
    standards_answers = StandardAnswer.objects.order_by("-standard_notification_date")

    # Show 10 standards_answers per page.
    standard_answer_list = standards_answers
    paginator = Paginator(standard_answer_list, 10)
    page_number = request.GET.get("page", 1)
    try:
        response = paginator.page(page_number)
    except PageNotAnInteger:
        response = paginator.page(1)
    except EmptyPage:
        response = paginator.page(paginator.num_pages)
    # add paggination to the regular view.
    f = StandardAnswerFilter(request.GET, queryset=standards_answers)
    html_view = "securityobjectives.html"
    if is_user_regulator(request.user):
        html_view = "regulator/securityobjectives.html"
    return render(
        request,
        html_view,
        context={
            "site_name": SITE_NAME,
            "paginator": paginator,
            "filter": f,
            "standard_answers": response,
        },
    )


@login_required
@otp_required
def get_form_list(request, form_list=None):
    """Initialize data for the preliminary notification."""
    if form_list is None:
        form_list = get_forms_list()
    return FormWizardView.as_view(
        form_list,
    )(request)


@login_required
@otp_required
def create_so(request, form_list=None, standard_answer_id=None):
    if form_list is None and standard_answer_id is not None:
        standard_answer = StandardAnswer.objects.get(id=standard_answer_id)
        form_list = get_forms_list(standard_answer=standard_answer)
    return SOWizardView.as_view(
        form_list,
    )(request)


# to select the standards
class FormWizardView(SessionWizardView):
    """Wizard to manage the preliminary form."""

    template_name = "sodeclaration.html"

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)

        context["steps"] = [
            _("Regulators"),
            _("Regulations"),
            _("Standards"),
        ]
        # used for the title of the page
        context["action"] = "Declare"

        return context

    def get_form(self, step=None, data=None, files=None):
        # active_company = get_active_company_from_session(self.request)
        if step is None:
            step = self.steps.current

        if step == "1":
            step0data = self.get_cleaned_data_for_step("0")
            if step0data is None:
                messages.warning(self.request, _("Please select 1 regulator"))

        if step == "2":
            step1data = self.get_cleaned_data_for_step("1")
            if step1data is None:
                messages.warning(self.request, _("Please select 1 regulation"))
            step0data = self.get_cleaned_data_for_step("0")
            if step0data is None:
                messages.warning(self.request, _("Please select 1 regulator"))

        form = super().get_form(step, data, files)
        return form

    def get_form_initial(self, step):
        if step == "1":
            step0data = self.get_cleaned_data_for_step("0")
            if step0data:
                ids = step0data.get("regulators", "")
                regulators = Regulator.objects.filter(id__in=ids)
                return self.initial_dict.get(step, {"regulators": regulators})

        if step == "2":
            regulators = None
            regulations = None
            step0data = self.get_cleaned_data_for_step("0")
            if step0data:
                ids = step0data.get("regulators", "")
                regulators = Regulator.objects.filter(id__in=ids)
            step1data = self.get_cleaned_data_for_step("1")
            if step1data:
                ids = step1data.get("regulations", "")
                regulations = Regulation.objects.filter(id__in=ids)
            return self.initial_dict.get(step, {"regulators": regulators, "regulations": regulations})

        return self.initial_dict.get(step, {})

    def done(self, form_list, **kwargs):
        user = self.request.user
        company = get_active_company_from_session(self.request)
        data = [form.cleaned_data for form in form_list]
        standards_id = []
        if data[2].get("standard"):
            for standard_data in data[2]["standard"]:
                try:
                    standard_id = int(standard_data)
                    standards_id.append(standard_id)
                except Exception:
                    pass

        for y in standards_id:
            standard = None
            standard = Standard.objects.get(id=y)
            if standard is not None:
                standardanswer = StandardAnswer.objects.create(
                    standard=standard,
                    is_reviewed=False,
                    submitter_user=user,
                    submitter_company=company,
                    creator_name=user.first_name+' '+user.last_name,
                    creator_company_name=company.identifier+':'+company.name
                )
                standardanswer.save()

        return HttpResponseRedirect("/securityobjectives")


class SOWizardView(SessionWizardView):
    """Wizard to manage the different workflows."""

    template_name = "sodeclaration.html"

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)

        context["steps"] = [
            _("Standard"),
            _("SecurityObjective"),
        ]
        # used for the title of the page
        context["action"] = "Declare"

        return context

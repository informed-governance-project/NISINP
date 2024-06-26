from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django_otp.decorators import otp_required
from django.utils.translation import gettext as _
from django.contrib import messages

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from formtools.wizard.views import SessionWizardView
from governanceplatform.helpers import (
    is_user_regulator,
)

from governanceplatform.settings import (
    SITE_NAME,
)

from .models import (
    StandardAnswer
)
from .forms import (
    get_forms_list,
)
from governanceplatform.models import Regulator


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

    # add paggination to the regular incidents view.
    html_view = "securityobjectives.html"
    if is_user_regulator(request.user):
        html_view = "regulator/securityobjectives.html"
    return render(
        request,
        html_view,
        context={
            "site_name": SITE_NAME,
            "paginator": paginator,
            # "filter": f,
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


# to select the standards
class FormWizardView(SessionWizardView):
    """Wizard to manage the preliminary form."""

    template_name = "sodeclaration.html"

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)

        context["steps"] = [
            _("Regulators"),
            _("Regulations"),
        ]
        context["action"] = "Create"

        return context

    def get_form(self, step=None, data=None, files=None):
        # active_company = get_active_company_from_session(self.request)
        if step is None:
            step = self.steps.current

        if step == "1":
            step1data = self.get_cleaned_data_for_step("0")
            if step1data is None:
                messages.warning(self.request, _("Please select at least 1 regulator"))

        form = super().get_form(step, data, files)
        return form

    def get_form_initial(self, step):
        if step == "1":
            step0data = self.get_cleaned_data_for_step("0")
            if step0data:
                ids = step0data.get("regulators", "")
                regulators = Regulator.objects.filter(id__in=ids)
                return self.initial_dict.get(step, {"regulators": regulators})

        return self.initial_dict.get(step, {})

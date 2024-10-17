from collections import defaultdict

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django_otp.decorators import otp_required

from .forms import SecurityObjectiveAnswerForm, SecurityObjectiveStatusForm
from .models import Standard


@login_required
@otp_required
def get_security_objectives(request):
    context = {}
    return render(request, "security_objectives/declaration.html", context=context)


@login_required
@otp_required
def declaration(request):
    """Initialize data for the security objectives declaration."""
    context = {}
    standard = Standard.objects.all().first()
    security_objectives_queryset = (
        standard.securityobjectivesinstandard_set.all().order_by("position")
    )
    security_objectives = defaultdict(lambda: defaultdict(lambda: []))

    for so_in_standard in security_objectives_queryset:
        security_objective = so_in_standard.security_objective
        security_measures = security_objective.securitymeasure_set.all()
        security_objective.status_form = SecurityObjectiveStatusForm(
            prefix=f"so_{security_objective.id}"
        )
        for measure in security_measures:
            security_objective = measure.security_objective
            maturity_level = measure.maturity_level
            measure.answer_form = SecurityObjectiveAnswerForm(
                prefix=f"measure_{measure.id}"
            )

            security_objectives[security_objective][maturity_level].append(measure)

    security_objectives = {
        so: dict(levels) for so, levels in security_objectives.items()
    }

    context = {"security_objectives": security_objectives}

    return render(request, "security_objectives/declaration.html", context=context)


@login_required
@otp_required
def create_so(request):
    context = {}
    return render(request, "security_objectives/declaration.html", context=context)

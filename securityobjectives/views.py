from collections import defaultdict

from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render
from django_otp.decorators import otp_required

from .forms import SecurityObjectiveAnswerForm
from .models import SecurityMeasure


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
    security_measures = SecurityMeasure.objects.annotate(
        evidence_count=Count("evidence")
    ).order_by(
        "security_objective__position",
    )

    security_objectives = defaultdict(
        lambda: defaultdict(lambda: {"measures": [], "evidence_count": 0})
    )

    for measure in security_measures:
        security_objective = measure.security_objective
        maturity_level = measure.maturity_level
        evidences_list = []
        for evidence in measure.evidence_set.all():
            evidence.so_answer_form = SecurityObjectiveAnswerForm(
                prefix=f"evidence_{evidence.id}"
            )
            evidences_list.append(evidence)

        measure.evidences = evidences_list

        security_objectives[security_objective][maturity_level]["measures"].append(
            measure
        )
        security_objectives[security_objective][maturity_level][
            "evidence_count"
        ] += measure.evidence_count

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

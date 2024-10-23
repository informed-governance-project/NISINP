import json
import os
from collections import defaultdict

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Case, Count, ExpressionWrapper, F, FloatField, Value, When
from django.forms.models import model_to_dict
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext as _
from django_otp.decorators import otp_required
from weasyprint import CSS, HTML

from governanceplatform.helpers import (
    get_active_company_from_session,
    is_user_regulator,
)

from .forms import (
    SecurityObjectiveAnswerForm,
    SecurityObjectiveStatusForm,
    SelectSOStandardForm,
    SelectYearForm,
)
from .models import SecurityMeasure, SecurityMeasureAnswer, Standard, StandardAnswer


@login_required
@otp_required
def get_security_objectives(request):
    user = request.user

    standard_answers = (
        StandardAnswer.objects.filter(submitter_user=user)
        .annotate(
            total_security_objectives=Count(
                "standard__securityobjectivesinstandard__security_objective",
                distinct=True,
            ),
            total_security_objectives_answered=Count(
                "securitymeasureanswers__security_measure__security_objective",
                distinct=True,
            ),
            answered_percentage=Case(
                When(total_security_objectives=0, then=Value(0.0)),
                default=ExpressionWrapper(
                    F("total_security_objectives_answered")
                    * 100.0
                    / F("total_security_objectives"),
                    output_field=FloatField(),
                ),
            ),
        )
        .order_by("standard_notification_date")
    )

    context = {"standard_answers": standard_answers}
    return render(
        request, "security_objectives/securityobjectives.html", context=context
    )


@login_required
@otp_required
def select_so_standard(request):
    standard_list = [
        (standard.id, str(standard)) for standard in Standard.objects.all()
    ]
    if request.method == "POST":
        form = SelectSOStandardForm(request.POST, initial=standard_list)
        if form.is_valid():
            so_standard_id = form.cleaned_data["so_standard"]
            year = form.cleaned_data["year"]
            try:
                standard = Standard.objects.get(pk=so_standard_id)
                user = request.user
                company = get_active_company_from_session(request)
                new_standard_answer = StandardAnswer(
                    standard=standard,
                    submitter_user=user,
                    submitter_company=company,
                    creator_name=user.get_full_name(),
                    creator_company_name=str(company),
                    year_of_submission=year,
                )
                new_standard_answer.save()
                return redirect("so_declaration")
            except Standard.DoesNotExist:
                messages.error(request, _("Standard does not exist"))

    if not standard_list:
        messages.error(request, _("No data available"))
    form = SelectSOStandardForm(initial=standard_list)
    context = {"form": form}
    return render(request, "modals/select_so_standard.html", context=context)


@login_required
@otp_required
def declaration(request):
    """Initialize data for the security objectives declaration."""
    user = request.user
    standard_id = request.GET.get("id", None)
    if standard_id:
        try:
            standard_answer = StandardAnswer.objects.get(pk=standard_id)
        except StandardAnswer.DoesNotExist:
            pass
    else:
        standard_answer = (
            StandardAnswer.objects.filter(submitter_user=user)
            .order_by("standard_notification_date")
            .last()
        )

    standard = standard_answer.standard

    security_objectives_queryset = (
        standard.securityobjectivesinstandard_set.all().order_by("position")
    )

    if request.method == "POST":
        data = json.loads(request.body.decode("utf-8"))
        id_security_measure = data.pop("id", None)
        form = SecurityObjectiveAnswerForm(data)
        if form.is_valid():
            try:
                security_measure = SecurityMeasure.objects.get(pk=id_security_measure)
                field_name = next(iter(data))
                field_to_update = {field_name: form.cleaned_data[field_name]}
                obj, created = SecurityMeasureAnswer.objects.update_or_create(
                    standard_answer=standard_answer,
                    security_measure=security_measure,
                    defaults={
                        **field_to_update,
                        "security_measure_notification_date": timezone.now(),
                        "standard_answer": standard_answer,
                        "security_measure": security_measure,
                    },
                )

                if (
                    not obj.is_implemented
                    and not obj.comment
                    and not obj.review_comment
                ):
                    obj.delete()

                return JsonResponse(
                    {
                        "success": True,
                        "created": created,
                        "data": field_to_update,
                    },
                    status=201 if created else 200,
                )
            except SecurityMeasure.DoesNotExist:
                return JsonResponse(
                    {"success": False, "error": "security_measure_does_not_exist"},
                    status=404,
                )

    security_objectives = defaultdict(lambda: defaultdict(lambda: []))

    for so_in_standard in security_objectives_queryset:
        security_objective = so_in_standard.security_objective
        security_measures = security_objective.securitymeasure_set.all()
        security_objective.status_form = SecurityObjectiveStatusForm(
            prefix=f"so_{security_objective.id}"
        )
        for measure in security_measures:
            try:
                sm_answer = SecurityMeasureAnswer.objects.get(
                    standard_answer=standard_answer,
                    security_measure=measure,
                )
                initial = model_to_dict(
                    sm_answer, fields=["comment", "is_implemented", "review_comment"]
                )
            except SecurityMeasureAnswer.DoesNotExist:
                initial = {}

            initial["is_regulator"] = is_user_regulator(user)

            security_objective = measure.security_objective
            maturity_level = measure.maturity_level
            measure.answer_form = SecurityObjectiveAnswerForm(
                initial=initial, prefix=f"{measure.id}"
            )

            security_objectives[security_objective][maturity_level].append(measure)

    security_objectives = {
        so: dict(levels) for so, levels in security_objectives.items()
    }

    context = {"security_objectives": security_objectives}

    return render(request, "security_objectives/declaration.html", context=context)


@login_required
@otp_required
def copy_declaration(request, standard_answer_id: int):
    user = request.user
    if request.method == "POST":
        form = SelectYearForm(request.POST)
        if form.is_valid():
            year = form.cleaned_data["year"]
            try:
                original_standard_answer = StandardAnswer.objects.get(
                    pk=standard_answer_id
                )
                original_standard_answer_dict = {
                    "standard": original_standard_answer.standard,
                    "submitter_company": original_standard_answer.submitter_company,
                    "creator_company_name": original_standard_answer.creator_company_name,
                }

                new_standard_answer = StandardAnswer(
                    **original_standard_answer_dict,
                    submitter_user=user,
                    creator_name=user.get_full_name(),
                    year_of_submission=year,
                )
                new_standard_answer.save()

                security_measure_answers = SecurityMeasureAnswer.objects.filter(
                    standard_answer=original_standard_answer
                )

                if security_measure_answers:
                    security_measure_answers_copy = [
                        SecurityMeasureAnswer(
                            standard_answer=new_standard_answer,
                            security_measure=sma.security_measure,
                            comment=sma.comment,
                            is_implemented=sma.is_implemented,
                        )
                        for sma in security_measure_answers
                    ]

                    SecurityMeasureAnswer.objects.bulk_create(
                        security_measure_answers_copy
                    )

                messages.info(
                    request,
                    _("The security objectives declaration has been duplicated."),
                )
            except StandardAnswer.DoesNotExist:
                messages.error(request, _("Declaration not found"))

        return redirect("securityobjectives")

    form = SelectYearForm()
    context = {"form": form, "standard_answer_id": standard_answer_id}
    return render(request, "modals/copy_so_declaration.html", context=context)


@login_required
@otp_required
def submit_declaration(request, standard_answer_id: int):
    try:
        standard_answer = StandardAnswer.objects.get(pk=standard_answer_id)
        standard_answer.status = "DELIV"
        standard_answer.save()
        messages.info(
            request, _("The security objectives declaration has been submitted.")
        )
    except StandardAnswer.DoesNotExist:
        messages.error(request, _("Declaration not found"))
    return redirect("securityobjectives")


@login_required
@otp_required
def delete_declaration(request, standard_answer_id: int):
    try:
        standard_answer = StandardAnswer.objects.get(pk=standard_answer_id)
        standard_answer.delete()
        messages.info(
            request, _("The security objectives declaration has been deleted.")
        )
    except StandardAnswer.DoesNotExist:
        messages.error(request, _("Declaration not found"))
    return redirect("securityobjectives")


@login_required
@otp_required
def download_declaration_pdf(request, standard_answer_id: int):
    standard_answer = StandardAnswer.objects.filter(pk=standard_answer_id).annotate(
        total_security_objectives=Count(
            "standard__securityobjectivesinstandard__security_objective",
            distinct=True,
        ),
        total_security_objectives_answered=Count(
            "securitymeasureanswers__security_measure__security_objective",
            distinct=True,
        ),
        answered_percentage=Case(
            When(total_security_objectives=0, then=Value(0.0)),
            default=ExpressionWrapper(
                F("total_security_objectives_answered")
                * 100.0
                / F("total_security_objectives"),
                output_field=FloatField(),
            ),
        ),
    )

    if not standard_answer:
        messages.error(request, _("Declaration not found"))
        return redirect("securityobjectives")

    try:
        standard_answer = standard_answer.first()
        standard = standard_answer.standard
        security_objectives_queryset = (
            standard.securityobjectivesinstandard_set.all().order_by("position")
        )
        security_objectives = defaultdict(lambda: defaultdict(lambda: []))

        for so_in_standard in security_objectives_queryset:
            security_objective = so_in_standard.security_objective
            security_measures = security_objective.securitymeasure_set.all()
            for measure in security_measures:
                try:
                    sm_answer = SecurityMeasureAnswer.objects.get(
                        standard_answer=standard_answer,
                        security_measure=measure,
                    )
                    measure.is_implemented = sm_answer.is_implemented
                    measure.comment = sm_answer.comment
                    measure.review_comment = sm_answer.review_comment
                except SecurityMeasureAnswer.DoesNotExist:
                    measure.is_implemented = False

                security_objective = measure.security_objective
                maturity_level = measure.maturity_level
                security_objectives[security_objective][maturity_level].append(measure)

        security_objectives = {
            so: dict(levels) for so, levels in security_objectives.items()
        }
        static_theme_dir = settings.STATIC_THEME_DIR
        output_from_parsed_template = render_to_string(
            "security_objectives/report/template.html",
            {
                "static_theme_dir": os.path.abspath(static_theme_dir),
                "standard_answer": standard_answer,
                "security_objectives": security_objectives,
            },
            request=request,
        )

        htmldoc = HTML(string=output_from_parsed_template, base_url=static_theme_dir)

        stylesheets = [
            CSS(os.path.join(static_theme_dir, "css/custom.css")),
            CSS(os.path.join(static_theme_dir, "css/report.css")),
        ]

        pdf_report = htmldoc.write_pdf(stylesheets=stylesheets)
        response = HttpResponse(pdf_report, content_type="application/pdf")
        response[
            "Content-Disposition"
        ] = f"attachment;filename=Security_objective_declaration_{timezone.now().date()}.pdf"

        return response
    except Exception:
        messages.warning(request, _("An error occurred while generating the report."))
        return redirect("securityobjectives")

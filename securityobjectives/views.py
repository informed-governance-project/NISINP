import json
import os
from collections import defaultdict

import openpyxl
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
    is_user_operator,
    is_user_regulator,
)
from governanceplatform.models import Company

from .forms import (
    ImportSOForm,
    SecurityObjectiveAnswerForm,
    SecurityObjectiveStatusForm,
    SelectSOStandardForm,
    SelectYearForm,
)
from .models import (
    SecurityMeasure,
    SecurityMeasureAnswer,
    SecurityObjective,
    SecurityObjectiveStatus,
    Standard,
    StandardAnswer,
)


@login_required
@otp_required
def get_security_objectives(request):
    user = request.user
    standard_answer_queryset = StandardAnswer.objects.none()
    if is_user_regulator(user):
        standard_answer_queryset = StandardAnswer.objects.exclude(status="UNDE")
    if is_user_operator(user):
        company = get_active_company_from_session(request)
        standard_answer_queryset = StandardAnswer.objects.filter(
            submitter_company=company
        )

    standard_answers = standard_answer_queryset.annotate(
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
    ).order_by("standard_notification_date")

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

    if not has_change_permission(request, standard_answer, "edit"):
        return redirect("securityobjectives")

    standard = standard_answer.standard

    security_objectives_queryset = (
        standard.securityobjectivesinstandard_set.all().order_by("position")
    )

    if request.method == "POST":
        data = json.loads(request.body.decode("utf-8"))
        id_object = data.pop("id", None)
        field_name = next(iter(data))
        if field_name in ["review_comment", "status"] and not is_user_regulator(user):
            return JsonResponse(
                {
                    "success": False,
                    "error": f"No permission to update the {field_name}",
                },
                status=403,
            )
        if field_name == "status":
            form = SecurityObjectiveStatusForm(data)
            if form.is_valid():
                try:
                    security_objective = SecurityObjective.objects.get(pk=id_object)
                    field_to_update = {field_name: form.cleaned_data[field_name]}
                    obj, created = SecurityObjectiveStatus.objects.update_or_create(
                        standard_answer=standard_answer,
                        security_objective=security_objective,
                        defaults={
                            **field_to_update,
                            "standard_answer": standard_answer,
                            "security_objective": security_objective,
                        },
                    )

                    status_counts_queryset = (
                        SecurityObjectiveStatus.objects.filter(
                            standard_answer=standard_answer
                        )
                        .values("status")
                        .annotate(count=Count("status"))
                    )

                    status_counts_dict = defaultdict(
                        int,
                        {
                            item["status"]: item["count"]
                            for item in status_counts_queryset
                        },
                    )

                    security_objectives_count = security_objectives_queryset.count()

                    if sum(status_counts_dict.values()) == security_objectives_count:
                        pass_counts = status_counts_dict["PASS"]
                        fail_counts = status_counts_dict["FAIL"]

                        if pass_counts == security_objectives_count:
                            standard_answer.status = "PASS"
                        elif fail_counts >= 1:
                            standard_answer.status = "FAIL"
                        else:
                            standard_answer.status = "DELIV"

                        standard_answer.save()

                    return JsonResponse(
                        {
                            "success": True,
                            "created": created,
                            "id": id_object,
                            "data": field_to_update,
                        },
                        status=201 if created else 200,
                    )
                except SecurityObjective.DoesNotExist:
                    return JsonResponse(
                        {
                            "success": False,
                            "error": "security objective does not exist",
                        },
                        status=404,
                    )

        else:
            form = SecurityObjectiveAnswerForm(data)
            if form.is_valid():
                try:
                    security_measure = SecurityMeasure.objects.get(pk=id_object)
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
                        {"success": False, "error": "security measure does not exist"},
                        status=404,
                    )

    security_objectives = defaultdict(lambda: defaultdict(lambda: []))

    for so_in_standard in security_objectives_queryset:
        security_objective = so_in_standard.security_objective
        security_measures = security_objective.securitymeasure_set.all().order_by(
            "maturity_level__level"
        )
        try:
            so_status = SecurityObjectiveStatus.objects.get(
                standard_answer=standard_answer,
                security_objective=security_objective,
            )
            initial = model_to_dict(so_status, fields=["status"])
        except SecurityObjectiveStatus.DoesNotExist:
            initial = {}

        security_objective.status_form = SecurityObjectiveStatusForm(
            initial=initial, prefix=f"{security_objective.id}"
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
    try:
        original_standard_answer = StandardAnswer.objects.get(pk=standard_answer_id)
        if not has_change_permission(request, original_standard_answer, "copy"):
            return redirect("securityobjectives")
    except StandardAnswer.DoesNotExist:
        messages.error(request, _("Declaration not found"))
        return redirect("securityobjectives")
    if request.method == "POST":
        form = SelectYearForm(request.POST)
        if form.is_valid():
            year = form.cleaned_data["year"]
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

                SecurityMeasureAnswer.objects.bulk_create(security_measure_answers_copy)

            messages.info(
                request,
                _("The security objectives declaration has been duplicated."),
            )

        return redirect("securityobjectives")

    form = SelectYearForm()
    context = {"form": form, "standard_answer_id": standard_answer_id}
    return render(request, "modals/copy_so_declaration.html", context=context)


@login_required
@otp_required
def submit_declaration(request, standard_answer_id: int):
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

    standard_answer = standard_answer.first()
    if not has_change_permission(request, standard_answer, "submit"):
        return redirect("securityobjectives")
    standard_answer.status = "DELIV"
    standard_answer.save()
    messages.info(request, _("The security objectives declaration has been submitted."))

    return redirect("securityobjectives")


@login_required
@otp_required
def delete_declaration(request, standard_answer_id: int):
    try:
        standard_answer = StandardAnswer.objects.get(pk=standard_answer_id)
        if not has_change_permission(request, standard_answer, "delete"):
            return redirect("securityobjectives")
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
        if not has_change_permission(request, standard_answer, "download"):
            return redirect("securityobjectives")
        standard = standard_answer.standard
        security_objectives_queryset = (
            standard.securityobjectivesinstandard_set.all().order_by("position")
        )
        security_objectives = defaultdict(lambda: defaultdict(lambda: []))

        for so_in_standard in security_objectives_queryset:
            security_objective = so_in_standard.security_objective
            security_measures = security_objective.securitymeasure_set.all().order_by(
                "maturity_level__level"
            )
            try:
                so_status = SecurityObjectiveStatus.objects.get(
                    standard_answer=standard_answer,
                    security_objective=security_objective,
                )
                security_objective.status = so_status
            except SecurityObjectiveStatus.DoesNotExist:
                security_objective.status = None

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


@login_required
@otp_required
def import_so_declaration(request):
    user = request.user
    standard_list = [
        (standard.id, str(standard)) for standard in Standard.objects.all()
    ]
    company_list = [(company.id, str(company)) for company in Company.objects.all()]
    if request.method == "POST":
        form = ImportSOForm(
            request.POST,
            request.FILES,
            initial={"standard": standard_list, "company": company_list},
        )
        if form.is_valid():
            try:
                wb = openpyxl.load_workbook(form.cleaned_data["import_file"])
                ws = wb.active
            except Exception as e:
                messages.error(request, _("Error opening the file: {}").format(str(e)))
                return redirect("securityobjectives")

            measure_answers_imported = []
            default_text = "Free text field"
            standard_id = form.cleaned_data["standard"]
            company_id = form.cleaned_data["company"]
            year = form.cleaned_data["year"]
            status = form.cleaned_data["status"]

            try:
                standard = Standard.objects.get(pk=standard_id)
                company = Company.objects.get(pk=company_id)
                users = company.user_set.filter(is_staff=True)
                if users:
                    user = users.first()
                else:
                    messages.warning(
                        request,
                        _("No users for this company"),
                    )

                new_standard_answer = StandardAnswer(
                    standard=standard,
                    status=status,
                    submitter_user=user,
                    submitter_company=company,
                    creator_name=user.get_full_name(),
                    year_of_submission=year,
                )
                new_standard_answer.save()
            except (Standard.DoesNotExist, Company.DoesNotExist):
                messages.warning(
                    request,
                    _("An error occurred while importing the declaration file."),
                )
                return redirect("securityobjectives")

            security_objectives = {
                obj.security_objective.unique_code: obj.security_objective
                for obj in standard.securityobjectivesinstandard_set.all()
            }

            for row in ws.iter_rows(
                min_row=4, max_row=120, max_col=9, values_only=True
            ):
                security_objective_code = row[1].split(":")[0] if row[1] else None
                if security_objective_code:
                    comment = (
                        row[7] if row[7] and default_text not in str(row[7]) else None
                    )
                    maturity_level = row[8] if isinstance(row[8], int) else None
                    if comment or maturity_level is not None:
                        maturity_level = maturity_level if maturity_level else 0
                        comment = comment if comment else ""

                        security_objective = security_objectives.get(
                            security_objective_code
                        )

                        if security_objective:
                            security_measures = SecurityMeasure.objects.filter(
                                security_objective=security_objective,
                                maturity_level__level__lte=maturity_level,
                            )

                            for sm in security_measures:
                                sma_comment = (
                                    comment
                                    if sm.maturity_level.level == maturity_level
                                    else ""
                                )
                                if sma_comment:
                                    comment = ""
                                is_implemented = (
                                    True
                                    if sm.maturity_level.level <= maturity_level
                                    and not sm.maturity_level.level == 0
                                    else False
                                )
                                measure_answers_imported.append(
                                    SecurityMeasureAnswer(
                                        standard_answer=new_standard_answer,
                                        security_measure=sm,
                                        comment=sma_comment,
                                        is_implemented=is_implemented,
                                    )
                                )

            SecurityMeasureAnswer.objects.bulk_create(measure_answers_imported)

            messages.info(
                request, ("The security objectives declaration has been imported.")
            )

            return redirect("securityobjectives")

    if not standard_list:
        messages.error(request, _("No data available"))
    form = ImportSOForm(
        initial={"standard": standard_list, "company": company_list},
    )
    context = {"form": form}
    return render(request, "modals/import_so_declaration.html", context=context)


def has_change_permission(request, standard_answer, action):
    def check_conditions():
        user = request.user
        user_company = get_active_company_from_session(request)
        is_standard_answer_in_user_company = (
            is_user_operator(user) and standard_answer.submitter_company == user_company
        )

        match action:
            case "edit":
                return (
                    is_user_regulator(user) and standard_answer.status != "UNDE"
                ) or (
                    is_standard_answer_in_user_company
                    and standard_answer.status == "UNDE"
                )
            case "submit":
                return (
                    is_standard_answer_in_user_company
                    and standard_answer.status == "UNDE"
                    and standard_answer.answered_percentage == 100
                )
            case "copy":
                return is_standard_answer_in_user_company
            case "delete":
                return (
                    is_standard_answer_in_user_company
                    and not standard_answer.status == "UNDE"
                )
            case "download":
                return (
                    is_user_regulator(user)
                    and standard_answer.status != "UNDE"
                    or is_standard_answer_in_user_company
                )
            case _:
                return False

    if not check_conditions():
        messages.error(request, _("Forbidden"))
        return False
    return True

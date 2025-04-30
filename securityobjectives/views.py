import json
import logging
import os
from collections import defaultdict
from math import modf

import openpyxl
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import (
    BooleanField,
    Case,
    Count,
    Exists,
    ExpressionWrapper,
    F,
    FloatField,
    OuterRef,
    Q,
    Value,
    When,
)
from django.db.models.functions import Cast
from django.forms.models import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext as _
from django_otp.decorators import otp_required
from weasyprint import CSS, HTML

from governanceplatform.helpers import (
    get_active_company_from_session,
    get_sectors_grouped,
    is_user_operator,
    is_user_regulator,
    user_in_group,
)
from governanceplatform.models import Company, CompanyUser, RegulatorUser, Sector

from .email import send_email
from .filters import StandardAnswerFilter
from .forms import (
    CopySOForm,
    ImportSOForm,
    ReviewForm,
    SecurityObjectiveAnswerForm,
    SecurityObjectiveStatusForm,
    SelectSOStandardForm,
)
from .globals import STANDARD_ANSWER_REVIEW_STATUS
from .models import (
    LogStandardAnswer,
    SecurityMeasure,
    SecurityMeasureAnswer,
    SecurityObjective,
    SecurityObjectiveStatus,
    Standard,
    StandardAnswer,
)

# Increasing weasyprint log level
for logger_name in ["weasyprint", "fontTools"]:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.ERROR)


@login_required
@otp_required
def get_security_objectives(request):
    user = request.user
    standard_answer_queryset = StandardAnswer.objects.none()
    template = "operator/so_dashboard.html"
    if is_user_regulator(user):
        regulator = user.regulators.first()
        template = "regulator/so_dashboard.html"
        is_regulator_admin = user_in_group(user, "RegulatorAdmin")
        if not is_regulator_admin:
            standard_answer_queryset = StandardAnswer.objects.filter(
                standard__regulator=regulator, sectors__in=user.get_sectors().all()
            )
        if is_regulator_admin:
            standard_answer_queryset = StandardAnswer.objects.filter(
                standard__regulator=regulator
            )

        standard_answer_queryset = standard_answer_queryset.exclude(status="UNDE")

    if is_user_operator(user):
        company = get_active_company_from_session(request)
        standard_answer_queryset = StandardAnswer.objects.filter(
            submitter_company=company
        )

    standard_answers = get_standard_answers_with_progress(standard_answer_queryset)

    # Filter
    if "reset" in request.GET:
        if "so_filter_params" in request.session:
            del request.session["so_filter_params"]
        return redirect("securityobjectives")

    if request.GET:
        request.session["so_filter_params"] = request.GET

    so_filter_params = request.session.get("so_filter_params", request.GET)
    security_objective_filter = StandardAnswerFilter(
        so_filter_params, queryset=standard_answers
    )

    # Filter
    so_answer_list = security_objective_filter.qs
    is_filtered = {k: v for k, v in so_filter_params.items() if k != "page"}

    context = {
        "standard_answers": so_answer_list,
        "filter": security_objective_filter,
        "is_filtered": bool(is_filtered),
    }
    return render(request, template, context=context)


@login_required
@otp_required
def create_so_declaration(request):
    standard_list = [
        (standard.id, str(standard))
        for standard in Standard.objects.filter(
            securityobjectivesinstandard__isnull=False
        ).distinct()
    ]

    sector_list = get_sectors_grouped(Sector.objects.all())
    if not standard_list or not sector_list:
        messages.error(request, _("No data available"))

    initial = {"standard_list": standard_list, "sectors_list": sector_list}
    if request.method == "POST":
        form = SelectSOStandardForm(request.POST, initial=initial)
        if form.is_valid():
            so_standard_id = form.cleaned_data["so_standard"]
            year = form.cleaned_data["year"]
            sectors = form.cleaned_data["sectors"]
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
                new_standard_answer.sectors.set(sectors)
                create_entry_log(user, new_standard_answer, "CREATE", request)
                return redirect("so_declaration")
            except Standard.DoesNotExist:
                messages.error(request, _("Standard does not exist"))

    form = SelectSOStandardForm(initial=initial)
    context = {"form": form}
    return render(request, "modals/create_so_declaration.html", context=context)


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
            messages.error(request, _("Declaration not found"))
            return redirect("securityobjectives")
    else:
        standard_answer = (
            StandardAnswer.objects.filter(submitter_user=user)
            .order_by("last_update")
            .last()
        )
    if not standard_answer:
        messages.error(request, _("Declaration not found"))
        return redirect("securityobjectives")

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
        if (
            field_name in ["is_implemented", "justification"]
            and not standard_answer.status == "UNDE"
        ):
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

                    standard_answer.last_update = timezone.now()
                    standard_answer.save()

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
                        old_status = standard_answer.status
                        if pass_counts == security_objectives_count:
                            standard_answer.status = "PASS"
                        elif fail_counts >= 1:
                            standard_answer.status = "FAIL"
                        else:
                            standard_answer.status = "DELIV"
                        if old_status != standard_answer.status:
                            send_email(
                                standard_answer.standard.security_objective_status_changed_email,
                                standard_answer,
                            )
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
                    sma, sma_created = SecurityMeasureAnswer.objects.update_or_create(
                        standard_answer=standard_answer,
                        security_measure=security_measure,
                        defaults={
                            **field_to_update,
                            "security_measure_notification_date": timezone.now(),
                            "standard_answer": standard_answer,
                            "security_measure": security_measure,
                        },
                    )

                    so_score = calculate_so_score(security_measure, standard_answer)

                    if so_score is not None:
                        SecurityObjectiveStatus.objects.update_or_create(
                            standard_answer=standard_answer,
                            security_objective=security_measure.security_objective,
                            defaults={
                                "score": so_score,
                                "standard_answer": standard_answer,
                                "security_objective": security_measure.security_objective,
                            },
                        )

                    if (
                        not sma.is_implemented
                        and not sma.justification
                        and not sma.review_comment
                    ):
                        sma.delete()

                    standard_answer.last_update = timezone.now()
                    standard_answer.save()
                    objective_state = get_completion_objective(
                        security_measure.security_objective, standard_answer
                    )
                    objective_state["id"] = security_measure.security_objective.pk

                    return JsonResponse(
                        {
                            "success": True,
                            "created": sma_created,
                            "data": field_to_update,
                            "objective_state": objective_state,
                        },
                        status=201 if sma_created else 200,
                    )
                except SecurityMeasure.DoesNotExist:
                    return JsonResponse(
                        {"success": False, "error": "security measure does not exist"},
                        status=404,
                    )

    security_objectives = defaultdict(lambda: defaultdict(lambda: []))

    for so_in_standard in security_objectives_queryset:
        security_objective = so_in_standard.security_objective
        security_objective.completion_state = get_completion_objective(
            security_objective, standard_answer
        )
        security_objective.declaration_status = standard_answer.status
        security_measures = security_objective.securitymeasure_set.all().order_by(
            "position"
        )
        try:
            so_status = SecurityObjectiveStatus.objects.get(
                standard_answer=standard_answer,
                security_objective=security_objective,
            )
            initial = model_to_dict(so_status, fields=["status"])
            security_objective.score = so_status.score
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
                    sm_answer,
                    fields=["justification", "is_implemented", "review_comment"],
                )
            except SecurityMeasureAnswer.DoesNotExist:
                initial = {}

            initial["is_regulator"] = is_user_regulator(user)
            initial["is_readonly"] = (
                is_user_operator(user) and standard_answer.status != "UNDE"
            )

            security_objective = measure.security_objective
            maturity_level = measure.maturity_level
            measure.answer_form = SecurityObjectiveAnswerForm(
                initial=initial, prefix=f"{measure.id}"
            )

            security_objectives[security_objective][maturity_level].append(measure)

    security_objectives = {
        so: dict(levels) for so, levels in security_objectives.items()
    }

    create_entry_log(user, standard_answer, "READ", request)

    context = {"security_objectives": security_objectives}

    return render(request, "security_objectives/declaration.html", context=context)


@login_required
@otp_required
def copy_declaration(request, standard_answer_id: int):
    user = request.user
    sector_list = get_sectors_grouped(Sector.objects.all())
    initial = {"sectors": sector_list}
    if not sector_list:
        messages.error(request, _("No sectors data available"))
    try:
        original_standard_answer = StandardAnswer.objects.get(pk=standard_answer_id)
        if not has_change_permission(request, original_standard_answer, "copy"):
            return redirect("securityobjectives")
    except StandardAnswer.DoesNotExist:
        messages.error(request, _("Declaration not found"))
        return redirect("securityobjectives")
    if request.method == "POST":
        form = CopySOForm(request.POST, initial=initial)
        if form.is_valid():
            year = form.cleaned_data["year"]
            sectors = form.cleaned_data["sectors"]
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
            new_standard_answer.sectors.set(sectors)
            create_entry_log(user, new_standard_answer, "CREATE", request)
            create_entry_log(user, original_standard_answer, "COPY", request)

            security_measure_answers = SecurityMeasureAnswer.objects.filter(
                standard_answer=original_standard_answer
            )

            if security_measure_answers:
                security_measure_answers_copy = [
                    SecurityMeasureAnswer(
                        standard_answer=new_standard_answer,
                        security_measure=sma.security_measure,
                        justification=sma.justification,
                        is_implemented=sma.is_implemented,
                    )
                    for sma in security_measure_answers
                ]

                SecurityMeasureAnswer.objects.bulk_create(security_measure_answers_copy)

                for sma in security_measure_answers_copy:
                    security_measure = sma.security_measure
                    standard_answer = sma.standard_answer
                    so_score = calculate_so_score(security_measure, standard_answer)

                    if so_score is not None:
                        SecurityObjectiveStatus.objects.update_or_create(
                            standard_answer=sma.standard_answer,
                            security_objective=sma.security_measure.security_objective,
                            defaults={
                                "score": so_score,
                                "standard_answer": standard_answer,
                                "security_objective": security_measure.security_objective,
                            },
                        )

            messages.success(
                request,
                _("The security objectives declaration has been duplicated."),
            )

        return redirect("securityobjectives")

    form = CopySOForm(initial=initial)
    context = {"form": form, "standard_answer_id": standard_answer_id}
    return render(request, "modals/copy_so_declaration.html", context=context)


@login_required
@otp_required
def submit_declaration(request, standard_answer_id: int):
    user = request.user
    standard_answer_queryset = StandardAnswer.objects.filter(pk=standard_answer_id)
    standard_answer = get_standard_answers_with_progress(standard_answer_queryset)

    if not standard_answer:
        messages.error(request, _("Declaration not found"))
        return redirect("securityobjectives")

    standard_answer = standard_answer.first()
    if not has_change_permission(request, standard_answer, "submit"):
        return redirect("securityobjectives")
    standard_answer.status = "DELIV"
    standard_answer.submit_date = timezone.now()
    standard_answer.save()
    send_email(standard_answer.standard.submission_email, standard_answer)
    create_entry_log(user, standard_answer, "SUBMIT", request)
    messages.success(
        request, _("The security objectives declaration has been submitted.")
    )

    return redirect("securityobjectives")


@login_required
@otp_required
def delete_declaration(request, standard_answer_id: int):
    try:
        standard_answer = StandardAnswer.objects.get(pk=standard_answer_id)
        if not has_change_permission(request, standard_answer, "delete"):
            return redirect("securityobjectives")
        standard_answer.delete()
        messages.success(
            request, _("The security objectives declaration has been deleted.")
        )
    except StandardAnswer.DoesNotExist:
        messages.error(request, _("Declaration not found"))
    return redirect("securityobjectives")


@login_required
@otp_required
def review_comment_declaration(request, standard_answer_id: int):
    user = request.user
    try:
        standard_answer = StandardAnswer.objects.get(pk=standard_answer_id)
        if not has_change_permission(request, standard_answer, "review_comment"):
            return redirect("securityobjectives")
    except StandardAnswer.DoesNotExist:
        messages.error(request, _("Declaration not found"))
        return redirect("securityobjectives")

    initial = model_to_dict(
        standard_answer, fields=["review_comment", "deadline", "status"]
    )
    if is_user_operator(user):
        create_entry_log(user, standard_answer, "READ", request)
        initial["is_readonly"] = is_user_operator(user)
    else:
        initial["is_readonly"] = not is_user_regulator(user)

    if request.method == "POST":
        form = ReviewForm(request.POST, initial=initial)
        if form.is_valid():
            standard_answer.review_comment = form.cleaned_data["review_comment"]
            standard_answer.deadline = form.cleaned_data["deadline"]
            standard_answer.last_update = timezone.now()
            standard_answer.save()
            email_to_send = False

            create_entry_log(user, standard_answer, "COMMENT", request)
            messages.success(
                request,
                _("The review comment has been saved."),
            )

            if standard_answer.status == STANDARD_ANSWER_REVIEW_STATUS[2][0]:
                standard_answer.status = STANDARD_ANSWER_REVIEW_STATUS[3][0]
                email_to_send = True
            elif standard_answer.status == STANDARD_ANSWER_REVIEW_STATUS[4][0]:
                standard_answer.status = STANDARD_ANSWER_REVIEW_STATUS[5][0]
                email_to_send = True
            if email_to_send:
                standard_answer.save()
                send_email(
                    standard_answer.standard.security_objective_status_changed_email,
                    standard_answer,
                )

            return redirect("securityobjectives")

    form = ReviewForm(initial=initial)
    context = {"form": form, "standard_answer_id": standard_answer_id}
    return render(request, "modals/review_comment_so_declaration.html", context=context)


@login_required
@otp_required
def access_log(request, standard_answer_id: int):
    user = request.user
    try:
        standard_answer = StandardAnswer.objects.get(pk=standard_answer_id)
        if not has_change_permission(request, standard_answer, "log"):
            return redirect("securityobjectives")
    except StandardAnswer.DoesNotExist:
        messages.error(request, _("Declaration not found"))
        return redirect("securityobjectives")

    log = LogStandardAnswer.objects.filter(standard_answer=standard_answer).order_by(
        "-timestamp"
    )
    if is_user_operator(user):
        log = log.exclude(user__regulatoruser__isnull=False)

    context = {"log": log}
    return render(request, "modals/so_access_log.html", context=context)


@login_required
@otp_required
def download_declaration_pdf(request, standard_answer_id: int):
    user = request.user
    standard_answer_queryset = StandardAnswer.objects.filter(pk=standard_answer_id)
    standard_answer = get_standard_answers_with_progress(standard_answer_queryset)

    if not standard_answer:
        messages.error(request, _("Declaration not found"))
        rendered_messages = render_error_messages(request)
        return JsonResponse({"messages": rendered_messages}, status=400)
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
            security_objective.declaration_status = standard_answer.status
            security_measures = security_objective.securitymeasure_set.all().order_by(
                "position"
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
                    measure.justification = sm_answer.justification
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
        create_entry_log(user, standard_answer, "DOWNLOAD", request)
        return response
    except Exception:
        messages.warning(request, _("An error occurred while generating the report."))
        return redirect("securityobjectives")


@login_required
@otp_required
def import_so_declaration(request):
    user = request.user
    regulator = user.regulators.first()
    standard_list = [
        (standard.id, str(standard))
        for standard in Standard.objects.filter(regulator=regulator)
    ]

    if not standard_list:
        messages.error(request, _("No data available"))
        return HttpResponseRedirect(request.headers.get("referer"))

    sectors_queryset = (
        user.get_sectors().all()
        if user_in_group(user, "RegulatorUser")
        else Sector.objects.all()
    )

    sector_list = get_sectors_grouped(sectors_queryset)

    companies_queryset = (
        Company.objects.filter(
            companyuser__sectors__in=user.get_sectors().values_list("id", flat=True)
        ).distinct()
        if user_in_group(user, "RegulatorUser")
        else Company.objects.all()
    )

    company_list = [(company.id, str(company)) for company in companies_queryset]

    try:
        initial = {}
        if "company_id" in request.GET:
            company_id = int(request.GET.get("company_id"))
            if not companies_queryset.filter(id=company_id).exists():
                messages.error(request, _("Forbidden"))
                return HttpResponseRedirect(request.headers.get("referer"))
            initial["company"] = company_id

        if "sector_id" in request.GET:
            sector_id = int(request.GET.get("sector_id"))
            if not sectors_queryset.filter(id=sector_id).exists():
                messages.error(request, _("Forbidden"))
                return HttpResponseRedirect(request.headers.get("referer"))
            initial["sectors"] = sector_id

        if "year" in request.GET:
            initial["year"] = int(request.GET.get("year"))

    except (ValueError, TypeError):
        messages.error(request, _("Invalid request"))
        return HttpResponseRedirect(request.headers.get("referer"))

    choices = {
        "standard": standard_list,
        "company": company_list,
        "sectors": sector_list,
    }

    if request.method == "POST":
        form = ImportSOForm(
            request.POST,
            request.FILES,
            initial=initial or {},
            choices=choices,
        )
        if form.is_valid():
            try:
                wb = openpyxl.load_workbook(form.cleaned_data["import_file"])
                ws = wb.active
            except Exception as e:
                messages.error(request, _("Error opening the file: {}").format(str(e)))
                return HttpResponseRedirect(request.headers.get("referer"))

            measure_answers_imported = []
            default_text = "Free text field"
            standard_id = form.cleaned_data["standard"]
            company_id = form.cleaned_data["company"]
            year = form.cleaned_data["year"]
            sectors = form.cleaned_data["sectors"]
            valid_sectors = []

            try:
                standard = Standard.objects.get(pk=standard_id)
                company = Company.objects.get(pk=company_id)
                users = company.user_set.filter(is_staff=True)
                if users:
                    user = users.first()
                else:
                    messages.error(
                        request,
                        _("No users for this company"),
                    )
                    return HttpResponseRedirect(request.headers.get("referer"))

                company_sectors = company.get_queryset_sectors()
                for sector in Sector.objects.filter(id__in=sectors):
                    if sector not in company_sectors:
                        messages.error(
                            request,
                            f"Sector error: {str(sector)} is not linked to the {str(company)}",
                        )
                    else:
                        valid_sectors.append(sector)

                if not valid_sectors:
                    return HttpResponseRedirect(request.headers.get("referer"))

                new_standard_answer = StandardAnswer(
                    standard=standard,
                    status=STANDARD_ANSWER_REVIEW_STATUS[1][0],  # Default UNDER REVIEW
                    submitter_user=user,
                    submitter_company=company,
                    creator_name=user.get_full_name(),
                    creator_company_name=str(company),
                    year_of_submission=year,
                    submit_date=timezone.now(),
                )
                new_standard_answer.save()
                new_standard_answer.sectors.set(valid_sectors)

            except (Standard.DoesNotExist, Company.DoesNotExist):
                messages.error(
                    request,
                    _("An error occurred while importing the declaration file."),
                )
                return HttpResponseRedirect(request.headers.get("referer"))

            security_objectives = {
                obj.security_objective.unique_code: obj.security_objective
                for obj in standard.securityobjectivesinstandard_set.all()
            }

            for row in ws.iter_rows(
                min_row=4, max_row=120, max_col=9, values_only=True
            ):
                security_objective_code = row[1].split(":")[0] if row[1] else None
                if security_objective_code:
                    evidence = (
                        row[6] if row[6] and default_text not in str(row[6]) else None
                    )
                    justification = (
                        row[7] if row[7] and default_text not in str(row[7]) else None
                    )
                    maturity_level = row[8] if isinstance(row[8], int) else None
                    if evidence or justification or maturity_level is not None:
                        maturity_level = maturity_level if maturity_level else 0
                        evidence = evidence if evidence else ""
                        justification = justification if justification else ""
                        evidence_and_justification = (
                            f"{evidence}\n\n{justification}"
                            if evidence
                            else justification
                        )

                        security_objective = security_objectives.get(
                            security_objective_code
                        )

                        if security_objective:
                            security_measures = SecurityMeasure.objects.filter(
                                security_objective=security_objective,
                                maturity_level__level__lte=maturity_level,
                            )

                            for sm in security_measures:
                                sma_justification = (
                                    evidence_and_justification
                                    if sm.maturity_level.level == maturity_level
                                    else ""
                                )
                                if sma_justification:
                                    evidence_and_justification = ""
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
                                        justification=sma_justification,
                                        is_implemented=is_implemented,
                                    )
                                )

            SecurityMeasureAnswer.objects.bulk_create(measure_answers_imported)

            for sma in measure_answers_imported:
                security_measure = sma.security_measure
                standard_answer = sma.standard_answer
                so_score = calculate_so_score(security_measure, standard_answer)

                if so_score is not None:
                    SecurityObjectiveStatus.objects.update_or_create(
                        standard_answer=sma.standard_answer,
                        security_objective=sma.security_measure.security_objective,
                        defaults={
                            "score": so_score,
                            "standard_answer": standard_answer,
                            "security_objective": security_measure.security_objective,
                        },
                    )

            create_entry_log(user, new_standard_answer, "IMPORT", request)
            messages.success(
                request, ("The security objectives declaration has been imported.")
            )
            return HttpResponseRedirect(request.headers.get("referer"))

    form = ImportSOForm(initial=initial or {}, choices=choices)
    context = {"form": form}
    return render(request, "modals/import_so_declaration.html", context=context)


def get_standard_answers_with_progress(standard_answer_queryset):
    invalid_answers = SecurityMeasureAnswer.objects.filter(
        standard_answer=OuterRef("pk"),
        security_measure__security_objective=OuterRef(
            "securitymeasureanswers__security_measure__security_objective"
        ),
        is_implemented=True,
        justification="",
    ).exclude(security_measure__maturity_level__level=0)

    standard_answers = standard_answer_queryset.annotate(
        total_security_objectives=Count(
            "standard__securityobjectivesinstandard__security_objective",
            distinct=True,
        ),
        total_security_objectives_answered=Count(
            "securitymeasureanswers__security_measure__security_objective",
            filter=Q(securitymeasureanswers__is_implemented=True)
            & ~Exists(invalid_answers),
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

    return standard_answers


def has_change_permission(request, standard_answer, action):
    def check_conditions():
        user = request.user
        user_sectors = user.get_sectors().all()
        user_company = get_active_company_from_session(request)
        is_standard_answer_in_user_company = (
            is_user_operator(user) and standard_answer.submitter_company == user_company
        )
        standard_sectors = standard_answer.sectors.all()
        is_user_regulator_sector = (
            user_in_group(user, "RegulatorAdmin")
            and standard_answer.standard.regulator == user.regulators.first()
        ) or (
            is_user_regulator(user)
            and standard_answer.standard.regulator == user.regulators.first()
            and any(sector in standard_sectors for sector in user_sectors)
        )

        match action:
            case "edit" | "download":
                return (
                    is_user_regulator_sector and standard_answer.status != "UNDE"
                ) or (is_standard_answer_in_user_company)
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
                    and standard_answer.status == "UNDE"
                ) or (is_user_regulator_sector)
            case "review_comment":
                return (
                    is_user_regulator_sector and standard_answer.status != "UNDE"
                ) or (
                    is_standard_answer_in_user_company
                    and (standard_answer.review_comment or standard_answer.deadline)
                )
            case "log":
                return is_user_regulator_sector or is_standard_answer_in_user_company
            case _:
                return False

    if not check_conditions():
        messages.error(request, _("Forbidden"))
        return False
    return True


def calculate_so_score(security_measure, standard_answer):
    try:
        scores_by_level = (
            SecurityMeasure.objects.filter(
                security_objective=security_measure.security_objective
            )
            .exclude(maturity_level__level=0)
            .values("maturity_level__level")
            .annotate(
                rate=Cast(
                    Count(
                        "securitymeasureanswers",
                        filter=Q(
                            securitymeasureanswers__is_implemented=True,
                            securitymeasureanswers__standard_answer=standard_answer,
                        ),
                    ),
                    FloatField(),
                )
                / Count("pk", distinct=True),
            )
            .order_by("maturity_level__level")
        )
    except Exception:
        return None

    final_score = scores_by_level[0]["rate"]
    for score in scores_by_level[1:]:
        if modf(final_score)[0] == 0 and score["rate"] > 0 and final_score > 0:
            final_score += score["rate"]
        else:
            break

    return final_score


def create_entry_log(user, standard_answer, action, request=None):
    role = _("User")
    entity_name = ""

    if is_user_operator(user) and request:
        active_company = get_active_company_from_session(request)
        cu = CompanyUser.objects.filter(user=user, company=active_company).first()
        if cu and cu.is_company_administrator:
            role = _("Administrator")
        entity_name = (
            active_company.name if active_company else user.companies.first().name
        )

    elif is_user_regulator(user):
        regulator = user.regulators.first()
        ru = RegulatorUser.objects.filter(user=user, regulator=regulator).first()
        if ru and ru.is_regulator_administrator:
            role = _("Administrator")
        entity_name = regulator.name

    log = LogStandardAnswer.objects.create(
        user=user,
        entity_name=entity_name,
        role=role,
        standard_answer=standard_answer,
        action=action,
    )
    log.save()


def get_completion_objective(security_objective, standard_answer):
    queryset = SecurityMeasureAnswer.objects.filter(
        security_measure__security_objective=security_objective,
        standard_answer=standard_answer,
    )
    if not queryset.exists():
        return {
            "is_completed": False,
            "is_partially": False,
            "is_not_started": True,
        }
    else:
        annotated_queryset = queryset.annotate(
            is_completed=Case(
                When(
                    Q(
                        is_implemented=True,
                        justification__gt="",
                    )
                    | Q(
                        security_measure__maturity_level__level=0,
                    ),
                    then=True,
                ),
                default=False,
                output_field=BooleanField(),
            ),
            is_partially=Case(
                When(
                    (
                        (Q(is_implemented=True) & Q(justification=""))
                        | (~Q(is_implemented=True) & Q(justification__gt=""))
                    )
                    & ~Q(security_measure__maturity_level__level=0),
                    then=True,
                ),
                default=False,
                output_field=BooleanField(),
            ),
        )

    completed_count = annotated_queryset.filter(is_completed=True).count()
    partially_count = annotated_queryset.filter(is_partially=True).count()

    total_count = annotated_queryset.count()
    all_completed = completed_count == total_count
    any_partially = partially_count > 0

    return {
        "is_completed": all_completed,
        "is_partially": any_partially,
        "is_not_started": total_count == 0,
    }


def render_error_messages(request):
    return render_to_string(
        "django_bootstrap5/messages.html",
        {"messages": messages.get_messages(request)},
        request=request,
    )

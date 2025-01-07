import secrets
from collections import defaultdict
from typing import Any, Optional

from django.contrib import messages
from django.db import connection
from django.http import HttpRequest
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from incidents.models import (
    Answer,
    Incident,
    PredefinedAnswer,
    Question,
    QuestionCategoryOptions,
    Workflow,
)
from securityobjectives.models import (
    Domain,
    MaturityLevel,
    SecurityMeasure,
    SecurityMeasureAnswer,
    SecurityObjective,
    SecurityObjectiveEmail,
    Standard,
    StandardAnswer,
)

from .models import Company, User


def table_exists(table_name: str) -> bool:
    """Checks if a table exists."""
    all_tables = connection.introspection.table_names()
    return table_name in all_tables


def generate_token():
    """Generates a random token-safe text string."""
    return secrets.token_urlsafe(32)[:32]


def user_in_group(user, group_name) -> bool:
    """Check user group"""
    if not user.is_authenticated:
        return False
    return any(user_group.name == group_name for user_group in user.groups.all())


def instance_user_in_group(user_instance, group_name) -> bool:
    return any(
        user_group.name == group_name for user_group in user_instance.groups.all()
    )


def is_user_regulator(user: User) -> bool:
    return user_in_group(user, "RegulatorAdmin") or user_in_group(user, "RegulatorUser")


def is_user_operator(user: User) -> bool:
    return user_in_group(user, "OperatorAdmin") or user_in_group(user, "OperatorUser")


def is_observer_user(user: User) -> bool:
    return user_in_group(user, "ObserverAdmin") or user_in_group(user, "ObserverUser")


def is_observer_user_viewving_all_incident(user: User) -> bool:
    return (is_observer_user(user)) and user.observers.first().is_receiving_all_incident


def get_active_company_from_session(request) -> Optional[Company]:
    company_in_use = request.session.get("company_in_use")
    return (
        request.user.companies.filter(id=company_in_use).first()
        if company_in_use
        else None
    )


def can_access_incident(user: User, incident: Incident, company_id=-1) -> bool:
    # if it's regulator incident
    if (
        is_user_regulator(user)
        and Incident.objects.filter(
            pk=incident.id,
            regulator=user.regulators.first(),
        ).exists()
    ):
        return True

    # RegulatorUser can access only incidents from accessible sectors.
    if (
        user_in_group(user, "RegulatorUser")
        and Incident.objects.filter(
            pk=incident.id, sector_regulation__regulator=user.regulators.first()
        ).exists()
    ):
        sectors = [
            sector
            for sector in incident.affected_sectors.all()
            if sector in user.get_sectors().all()
        ]
        if len(sectors) > 0:
            return True
        else:
            return False
    # RegulatorAdmin can access only incidents from accessible regulators.
    if (
        user_in_group(user, "RegulatorAdmin")
        and Incident.objects.filter(
            pk=incident.id, sector_regulation__regulator=user.regulators.first()
        ).exists()
    ):
        return True
    # OperatorAdmin can access only incidents related to selected company.
    if (
        user_in_group(user, "OperatorAdmin")
        and Incident.objects.filter(pk=incident.id, company__id=company_id).exists()
    ):
        return True
    # OperatorUser can access incidents related to selected company and sectors
    if (
        user_in_group(user, "OperatorUser")
        and Incident.objects.filter(
            pk=incident.id,
            company__id=company_id,
            affected_sectors__in=user.companyuser_set.all()
            .distinct()
            .values_list("sectors", flat=True),
        ).exists()
    ):
        return True
    # OperatorStaff and IncidentUser can access their reports.
    if (
        not is_user_regulator(user)
        and (user_in_group(user, "OperatorUser") or user_in_group(user, "IncidentUser"))
        and Incident.objects.filter(pk=incident.id, contact_user=user).exists()
    ):
        return True
    # ObserverUser access all incident if he is in a observer who can access all incident.
    if is_observer_user_viewving_all_incident(user):
        return True
    if is_observer_user(user):
        incident_lists = user.observers.first().get_incidents()
        if incident in incident_lists:
            return True

    return False


# check if the user is allowed to create an incident_workflow
def can_create_incident_report(user: User, incident: Incident, company_id=-1) -> bool:
    # if it's the incident of the user he can create
    if incident.contact_user == user:
        return True

    # if it's regulator incident
    if (
        is_user_regulator(user)
        and Incident.objects.filter(
            pk=incident.id,
            regulator=user.regulators.first(),
        ).exists()
    ):
        return True

    # if it's in his sector and user of the company
    if (
        user_in_group(user, "OperatorUser")
        and Incident.objects.filter(
            pk=incident.id,
            company__id=company_id,
            affected_sectors__in=user.companyuser_set.all()
            .distinct()
            .values_list("sectors", flat=True),
        ).exists()
    ):
        return True
    # if he is admin of the company he can create
    if (
        user_in_group(user, "OperatorAdmin")
        and Incident.objects.filter(pk=incident.id, company__id=company_id).exists()
    ):
        return True
    return False


# check if the user is allowed to edit an incident_workflow
# for regulators to add message
def can_edit_incident_report(user: User, incident: Incident, company_id=-1) -> bool:
    # if it's the incident of the user he can create
    if incident.contact_user == user:
        return True

    # if it's regulator incident
    if (
        is_user_regulator(user)
        and Incident.objects.filter(
            pk=incident.id,
            regulator=user.regulators.first(),
        ).exists()
    ):
        return True

    # if it's in his sector and user of the company
    if (
        user_in_group(user, "OperatorUser")
        and Incident.objects.filter(
            pk=incident.id,
            company__id=company_id,
            affected_sectors__in=user.companyuser_set.all()
            .distinct()
            .values_list("sectors", flat=True),
        ).exists()
    ):
        return True
    # if he is admin of the company he can create
    if (
        user_in_group(user, "OperatorAdmin")
        and Incident.objects.filter(pk=incident.id, company__id=company_id).exists()
    ):
        return True
    # if he is the regulator admin of the incident need to be link to his regulator
    if (
        user_in_group(user, "RegulatorAdmin")
        and incident.sector_regulation.regulator == user.regulators.first()
    ):
        return True
    # if he is the regulator user of the incident, he need to have the sectors
    if (
        user_in_group(user, "RegulatorUser")
        and incident.sector_regulation.regulator == user.regulators.first()
    ):
        sectors = [
            sector
            for sector in incident.affected_sectors.all()
            if sector in user.get_sectors().all()
        ]
        if len(sectors) > 0:
            return True
        else:
            return False

    return False


def set_creator(request: HttpRequest, obj: Any, change: bool) -> Any:
    regulator = request.user.regulators.first()
    if not change:
        obj.creator_name = regulator
        obj.creator_id = regulator.id

    if not obj.creator_name or not obj.creator_id:
        obj.creator_name = str(regulator)
        obj.creator_id = regulator.id
    return obj


def can_change_or_delete_obj(request: HttpRequest, obj: Any, check_request=True, send_message=True) -> bool:
    if check_request:
        if not hasattr(request, "_can_change_or_delete_obj"):
            request._can_change_or_delete_obj = True
        else:
            return request._can_change_or_delete_obj

    if not obj.pk:
        return True

    creator = getattr(obj, "creator", getattr(obj, "regulator", None))

    if not creator:
        return True

    in_use = True
    # [Predefined Answer] Check if obj is already in use
    if isinstance(obj, PredefinedAnswer):
        in_use = Answer.objects.filter(predefined_answers=obj).exists()

    # [Question Category] Check if obj is already in use
    if isinstance(obj, QuestionCategoryOptions):
        in_use = Answer.objects.filter(question_options__category_option=obj).exists()

    # [Question] Check if obj is already in use
    if isinstance(obj, Question):
        in_use = Answer.objects.filter(question_options__question=obj).exists()

    # [Workflow] in_use flag is set to False
    if isinstance(obj, Workflow):
        in_use = False

    # [Standard] Check if obj is already in use
    if isinstance(obj, Standard):
        in_use = StandardAnswer.objects.filter(standard=obj).exists()

    # [SecurityObjective] Check if obj is already in use
    if isinstance(obj, SecurityObjective):
        in_use = SecurityMeasureAnswer.objects.filter(
            security_measure__security_objective=obj
        ).exists()

    # [SecurityMeasure] Check if obj is already in use
    if isinstance(obj, SecurityMeasure):
        in_use = SecurityMeasureAnswer.objects.filter(security_measure=obj).exists()

    # [MaturityLevel] Check if obj is already in use
    if isinstance(obj, MaturityLevel):
        in_use = SecurityMeasureAnswer.objects.filter(
            security_measure__maturity_level=obj
        ).exists()

    # [Domain] Check if obj is already in use
    if isinstance(obj, Domain):
        in_use = SecurityMeasureAnswer.objects.filter(
            security_measure__security_objective__domain=obj
        ).exists()

    # [SecurityObjectiveEmail] Set in use flag to false
    if isinstance(obj, SecurityObjectiveEmail):
        in_use = False

    regulator = request.user.regulators.first()
    if creator == regulator and not in_use:
        return True

    verbose_name = obj._meta.verbose_name.lower()
    creator_name = creator
    if send_message:
        messages.warning(
            request,
            mark_safe(
                _(
                    f"<strong>Change or delete actions are not allowed</strong><br>"
                    f"- This {verbose_name} is either in use.<br>"
                    f"- You are not its creator ({creator_name})"
                )
            ),
        )
    request._can_change_or_delete_obj = False

    return False


# Remove languages are not translated
def filter_languages_not_translated(form):
    filtered_languages = [
        lang for lang in form.context_data["language_tabs"] if lang[3] != "empty"
    ]
    form.context_data["language_tabs"].allow_deletion = False
    form.context_data["language_tabs"] = filtered_languages

    return form


def get_sectors_grouped(sectors):
    categs = defaultdict(list)
    for sector in sectors:
        sector_name = sector.get_safe_translation()

        if sector.parent:
            parent_name = sector.parent.get_safe_translation()
            categs[parent_name].append([sector.id, sector_name])
        else:
            if not categs.get(sector_name):
                categs[sector_name].append([sector.id, sector_name])

    sectors_grouped = (
        (sector, sorted(options, key=lambda item: item[1]))
        for sector, options in categs.items()
    )

    return sorted(sectors_grouped, key=lambda item: item[0])

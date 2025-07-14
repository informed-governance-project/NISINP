from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.core.validators import validate_email
from django.template.loader import render_to_string
from django.urls import reverse

from governanceplatform.models import Observer, RegulatorUser
from incidents.globals import INCIDENT_EMAIL_VARIABLES


def is_valid_email(email):
    try:
        validate_email(email)
        return True
    except ValidationError:
        return False


# replace the variables in globals.py by the right value
def replace_email_variables(content, incident):
    # find the incidents which don't have final notification.
    modify_content = content
    modify_content = modify_content.replace("#PUBLIC_URL#", settings.PUBLIC_URL)
    for _i, (variable, key) in enumerate(INCIDENT_EMAIL_VARIABLES):
        if variable == "#INCIDENT_FINAL_NOTIFICATION_URL#":
            incident_id = getattr(incident, key)
            final_notification_url = settings.PUBLIC_URL + reverse(
                "final-notification", args=[incident_id]
            )
            var_txt = f'<a href="{final_notification_url}">{final_notification_url}</a>'

        else:
            var_txt = (
                getattr(incident, key) if getattr(incident, key) is not None else ""
            )
            if isinstance(var_txt, date):
                var_txt = getattr(incident, key).strftime("%Y-%m-%d")
        modify_content = modify_content.replace(variable, var_txt)
    return modify_content


def send_html_email(subject, content, recipient_list):
    recipient_list = [email for email in recipient_list if is_valid_email(email)]
    if recipient_list:
        email = EmailMessage(
            subject, content, settings.EMAIL_SENDER, bcc=recipient_list
        )
        email.content_subtype = "html"
        email.send(fail_silently=True)


def get_emails_from_qs(queryset):
    return [obj.user.email for obj in queryset]


def get_recipient_list(incident, send_to_observers):
    # Contact user's email
    recipient_list = [incident.contact_user.email]
    company = incident.company
    sector_regulation = incident.sector_regulation
    regulator = sector_regulation.regulator

    if company:
        # Company's email
        recipient_list.append(company.email)

        company_admins_qs = company.companyuser_set.filter(
            is_company_administrator=True
        ).select_related("user")
    else:
        company_admins_qs = []

    # Company administrators' emails
    recipient_list.extend(get_emails_from_qs(company_admins_qs))

    # Regulator's email
    recipient_list.append(regulator.email_for_notification)

    # Regulator administrators' emails
    regulator_admins_qs = regulator.regulatoruser_set.filter(
        is_regulator_administrator=True
    ).select_related("user")
    recipient_list.extend(get_emails_from_qs(regulator_admins_qs))

    # Sector managers' emails
    regulator_users_sectored = RegulatorUser.objects.filter(
        regulator=regulator,
        sectors__in=incident.affected_sectors.all(),
    ).distinct("user")
    recipient_list.extend(get_emails_from_qs(regulator_users_sectored))

    if send_to_observers:
        observer_emails = []
        observers = Observer.objects.all()
        for observer in observers:
            if observer.can_access_incident(incident):
                # Observer's mail
                observer_emails.append(observer.email_for_notification)
                # Observer users' email
                observer_user_qs = observer.observeruser_set.all().select_related(
                    "user"
                )
                observer_emails.extend(get_emails_from_qs(observer_user_qs))

        recipient_list.extend(observer_emails)

    # Remove duplicates
    recipient_list = list(dict.fromkeys(recipient_list))

    return recipient_list


def send_email(email, incident, send_to_observers=False):
    subject = replace_email_variables(email.subject, incident)
    html_content = render_to_string(
        "incidents/email.html",
        {
            "content": replace_email_variables(email.content, incident),
            "url_site": settings.PUBLIC_URL,
            "company_name": incident.company_name,
            "incident_contact_title": incident.contact_title,
            "incident_contact_firstname": incident.contact_firstname,
            "incident_contact_lastname": incident.contact_lastname,
            "technical_contact_title": incident.technical_title,
            "technical_contact_firstname": incident.technical_firstname,
            "technical_contact_lastname": incident.technical_lastname,
        },
    )
    recipient_list = get_recipient_list(incident, send_to_observers)

    send_html_email(subject, html_content, recipient_list)

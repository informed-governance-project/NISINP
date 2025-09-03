import logging
from datetime import date

import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.core.validators import validate_email
from django.template.loader import render_to_string
from django.urls import reverse

from governanceplatform.models import Observer, RegulatorUser
from incidents.globals import INCIDENT_EMAIL_VARIABLES

from .models import RTTicket

logger = logging.getLogger(__name__)


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
        elif variable == "#INCIDENT_DETECTION_DATE#":
            last_report = incident.get_latest_incident_workflow()
            if not last_report:
                var_txt = (
                    incident.incident_detection_date.strftime("%Y-%m-%d")
                    if incident.incident_detection_date is not None
                    else ""
                )
            else:
                var_txt = (
                    last_report.report_timeline.incident_detection_date.strftime("%Y-%m-%d")
                    if last_report.report_timeline.incident_detection_date is not None
                    else ""
                )
        elif variable == "#INCIDENT_STARTING_DATE#":
            last_report = incident.get_latest_incident_workflow()
            if not last_report:
                var_txt = ""
            else:
                var_txt = (
                    last_report.report_timeline.incident_starting_date.strftime("%Y-%m-%d")
                    if last_report.report_timeline.incident_starting_date is not None
                    else ""
                )
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


def get_recipient_list(incident):
    # Contact user's email
    recipient_list = []
    if incident.contact_user is not None:
        recipient_list.append(incident.contact_user.email)
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
    recipient_list = get_recipient_list(incident)

    if send_to_observers:
        observer_emails = []
        observers = Observer.objects.all()
        for observer in observers:
            if observer.can_access_incident(incident):
                if check_rt_config(observer):
                    create_or_update_rt_ticket(
                        observer, subject, html_content, incident
                    )
                else:
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

    send_html_email(subject, html_content, recipient_list)


def create_or_update_rt_ticket(recipient, subject, content, incident):
    is_new_ticket = not RTTicket.objects.filter(
        incident=incident, observer=recipient
    ).exists()
    base_url = recipient.rt_url.rstrip("/")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"token {recipient.rt_token}",
    }

    try:
        ticket = RTTicket.objects.filter(incident=incident, observer=recipient).first()
        is_new_ticket = ticket is None
        if is_new_ticket:
            url = f"{base_url}/REST/2.0/ticket"
            payload = {
                "Requestor": settings.EMAIL_SENDER,
                "Queue": recipient.rt_queue,
                "Subject": subject,
                "Content": content,
                "ContentType": "text/html",
            }
        else:
            url = f"{base_url}/REST/2.0/ticket/{ticket.ticket_id}/correspond"
            payload = {
                "Content": content,
                "ContentType": "text/html",
            }

        response = requests.post(url, json=payload, headers=headers, timeout=5)

        if response.ok:
            if is_new_ticket and response.status_code == 201:
                ticket_data = response.json()
                RTTicket.objects.create(
                    incident=incident,
                    observer=recipient,
                    ticket_id=ticket_data.get("id"),
                )
        else:
            logger.error(f"RT API Error {response.status_code}: {response.text}")
    except requests.RequestException as e:
        logger.error(f"Error connecting to RT API: {e}")


def check_rt_config(observer):
    if not observer.rt_url or not observer.rt_queue or not observer.rt_token:
        return False

    base_url = observer.rt_url.rstrip("/")
    url = f"{base_url}/REST/2.0/queue/{observer.rt_queue}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"token {observer.rt_token}",
    }
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            return True
        elif response.status_code == 401:
            logger.warning("RT token unauthorized (401) for %s", str(observer))
        elif response.status_code == 404:
            logger.warning("RT queue '%s' not found at %s", observer.rt_queue, url)
        else:
            logger.warning(
                "Unexpected RT response (%s): %s", response.status_code, response.text
            )
        return False
    except requests.RequestException as e:
        logger.error(f"Error connecting to RT API: {e}")
        return False

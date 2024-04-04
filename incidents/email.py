from datetime import date

from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.urls import reverse

from governanceplatform.config import EMAIL_SENDER, PUBLIC_URL
from governanceplatform.models import RegulatorUser
from incidents.globals import INCIDENT_EMAIL_VARIABLES


# replace the variables in globals.py by the right value
def replace_email_variables(content, incident):
    # find the incidents which don't have final notification.
    modify_content = content
    modify_content = modify_content.replace("#PUBLIC_URL#", PUBLIC_URL)
    for _i, (variable, key) in enumerate(INCIDENT_EMAIL_VARIABLES):
        if variable == "#INCIDENT_FINAL_NOTIFICATION_URL#":
            incident_id = getattr(incident, key)
            final_notification_url = PUBLIC_URL + reverse(
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
    email = EmailMessage(subject, content, EMAIL_SENDER, bcc=recipient_list)
    email.content_subtype = "html"
    email.send(fail_silently=True)


def send_email(email, incident):
    subject = replace_email_variables(email.subject, incident)
    html_content = render_to_string(
        "email.html",
        {
            "content": replace_email_variables(email.content, incident),
            "url_site": PUBLIC_URL,
            "company_name": incident.company_name,
            "incident_contact_title": incident.contact_title,
            "incident_contact_firstname": incident.contact_firstname,
            "incident_contact_lastname": incident.contact_lastname,
            "technical_contact_title": incident.technical_title,
            "technical_contact_firstname": incident.technical_firstname,
            "technical_contact_lastname": incident.technical_lastname,
        },
    )
    recipient_list = [incident.contact_user.email]
    # get also regulator email and emails of responsible people for the designated sectors
    sector_regulation = incident.sector_regulation
    regulator_email = sector_regulation.regulator.email_for_notification
    recipient_list.append(regulator_email)

    regulator_users_sectored = RegulatorUser.objects.filter(
        regulator=sector_regulation.regulator,
        sectors__in=incident.affected_sectors.all(),
    ).distinct("user")
    regulator_users_sectored_emails = []
    for u in regulator_users_sectored:
        regulator_users_sectored_emails.append(u.user.email)

    recipient_list.extend(regulator_users_sectored_emails)

    send_html_email(subject, html_content, recipient_list)

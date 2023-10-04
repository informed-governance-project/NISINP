from datetime import date

from django.core.mail import EmailMessage
from django.template import loader

from governanceplatform.config import EMAIL_SENDER, PUBLIC_URL
from incidents.globals import INCIDENT_EMAIL_VARIABLES


# replace the variables in globals.py by the right value
def replace_email_variables(content, incident):
    # find the incidents which don't have final notification.
    modify_content = content
    for variable in INCIDENT_EMAIL_VARIABLES:
        if variable[0] == "#INCIDENT_FINAL_NOTIFICATION_URL#":
            var_txt = PUBLIC_URL + "/incidents/final-notification/" + str(incident.pk)
        else:
            var_txt = getattr(incident, variable[1])
            if isinstance(var_txt, date):
                var_txt = getattr(incident, variable[1]).strftime("%Y-%m-%d")
        modify_content = modify_content.replace(variable[0], var_txt)
    return modify_content


def send_html_email(subject, context, recipient_list):
    template = loader.get_template("email.html")
    html_content = template.render(context)
    email = EmailMessage(subject, html_content, EMAIL_SENDER, recipient_list)
    email.content_subtype = "html"
    email.send(fail_silently=True)


def send_email(email, incident):
    subject = replace_email_variables(email.subject, incident)
    context = {
        "content": replace_email_variables(email.content, incident),
        "company_name": incident.company_name,
        "incident_contact_title": incident.contact_title,
        "incident_contact_firstname": incident.contact_firstname,
        "incident_contact_lastname": incident.contact_lastname,
        "technical_contact_title": incident.technical_title,
        "technical_contact_firstname": incident.technical_firstname,
        "technical_contact_lastname": incident.technical_lastname,
    }

    recipient_list = [incident.contact_user.email]

    send_html_email(subject, context, recipient_list)

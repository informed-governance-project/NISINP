from django.core.mail import EmailMessage
from django.template.loader import render_to_string

from governanceplatform.config import EMAIL_SENDER, PUBLIC_URL
from governanceplatform.models import RegulatorUser


def send_html_email(subject, content, recipient_list):
    email = EmailMessage(subject, content, EMAIL_SENDER, bcc=recipient_list)
    email.content_subtype = "html"
    email.send(fail_silently=True)


def send_email(email, standard_answer):
    if email is not None:
        subject = email.subject
        html_content = render_to_string(
            "security_objectives/email.html",
            {
                "content": email.content,
                "url_site": PUBLIC_URL,
            },
        )
        if standard_answer.submitter_user is not None:
            recipient_list = [standard_answer.submitter_user.email]
        # get also regulator email and emails of responsible people for the designated sectors
        regulator_email = standard_answer.standard.regulator.email_for_notification
        if regulator_email is not None:
            recipient_list.append(regulator_email)

        regulator_users_sectored = RegulatorUser.objects.filter(
            regulator=standard_answer.standard.regulator,
            sectors__in=standard_answer.sectors.all(),
        ).distinct("user")
        regulator_users_sectored_emails = []
        for u in regulator_users_sectored:
            regulator_users_sectored_emails.append(u.user.email)

        recipient_list.extend(regulator_users_sectored_emails)

        send_html_email(subject, html_content, recipient_list)

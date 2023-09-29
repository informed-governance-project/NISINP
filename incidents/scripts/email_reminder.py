from datetime import date

from dateutil.relativedelta import relativedelta
from django.core.mail import send_mail
from governanceplatform.config import EMAIL_SENDER
from incidents.models import Email, Incident
from incidents.email import replace_email_variables


# Script to run once a day
def run():
    # find the incidents which don't have final notification.
    for incident in Incident.objects.filter(final_notification_date=None):
        for email in Email.objects.filter(email_type="REMIND"):
            if incident.preliminary_notification_date == date.today() - relativedelta(
                days=email.days_before_send
            ):
                send_mail(
                    replace_email_variables(email.subject, incident),
                    replace_email_variables(email.content, incident),
                    EMAIL_SENDER,
                    [incident.contact_user.email],
                    fail_silently=True,
                )

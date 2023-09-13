from datetime import date

from dateutil.relativedelta import relativedelta
from django.core.mail import send_mail
from nisinp.config import EMAIL_SENDER
from nisinp.globals import INCIDENT_EMAIL_VARIABLES
from nisinp.models import Email, Incident


# Script to run once a day
def run():
    # find the incidents which don't have final notification.
    for incident in Incident.objects.filter(final_notification_date=None):
        for email in Email.objects.filter(email_type="REMIND"):
            if incident.preliminary_notification_date == date.today() - relativedelta(
                days=email.days_before_send
            ):
                content = email.content
                for variable in INCIDENT_EMAIL_VARIABLES:
                    var_txt = getattr(incident, variable[1])
                    if isinstance(var_txt, date):
                        var_txt = getattr(incident, variable[1]).strftime("%m/%d/%Y")
                    content = email.content.replace(variable[0], var_txt)
                send_mail(
                    email.subject,
                    content,
                    EMAIL_SENDER,
                    [incident.contact_user.email],
                    fail_silently=True,
                )

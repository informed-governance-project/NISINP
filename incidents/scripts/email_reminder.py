from datetime import date

from dateutil.relativedelta import relativedelta

from incidents.email import send_email
from incidents.models import Email, Incident


# Script to run once a day
def run():
    # find the incidents which don't have final notification.
    for incident in Incident.objects.filter(final_notification_date=None):
        for email in Email.objects.filter(email_type="REMIND"):
            if incident.preliminary_notification_date == date.today() - relativedelta(
                days=email.days_before_send
            ):
                send_email(email, incident)

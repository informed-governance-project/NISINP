from datetime import date

from governanceplatform.config import PUBLIC_URL
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

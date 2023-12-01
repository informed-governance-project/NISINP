QUESTION_TYPES = [
    ("FREETEXT", "Freetext"),
    ("MULTI", "Multiple Choice"),
    ("SO", "Single Option Choice"),
    ("MT", "Multiple Choice + Free Text"),
    ("ST", "Single Choice + Free Text"),
    ("CL", "Country list"),
    ("RL", "Region list"),
    ("DATE", "Date picker"),
]

REGIONAL_AREA = [
    ("LU_CA", "Capellen"),
    ("LU_CL", "Clervaux"),
    ("LU_DI", "Diekirch"),
    ("LU_EC", "Echternach"),
    ("LU_ES", "Esch-sur-Alzette"),
    ("LU_GR", "Grevenmacher"),
    ("LU_LU", "Luxembourg"),
    ("LU_ME", "Mersch"),
    ("LU_RE", "Redange"),
    ("LU_REM", "Remich"),
    ("LU_VI", "Vianden"),
    ("LU_WI", "Wiltz"),
]


# The variables to use in the email template in the admin interface, and the corresponding attribute
INCIDENT_EMAIL_VARIABLES = [
    ("#INCIDENT_NOTIFICATION_DATE#", "incident_notification_date"),
    ("#INCIDENT_DETECTION_DATE#", "incident_detection_date"),
    ("#INCIDENT_STARTING_DATE#", "incident_starting_date"),
    ("#INCIDENT_ID#", "incident_id"),
]

# the different trigger on when to send an email to the Incident.User
INCIDENT_EMAIL_TRIGGER_EVENT = [
    ("NOTIF_DATE", "Notification Date"),
    ("PREV_WORK", "Previous Workflow"),
]

INCIDENT_STATUS = [
    ("CLOSE", "Closed"),
    ("GOING", "On-going"),
]

REVIEW_STATUS = [
    ("DELIV", "Delivered but not yet reviewed"),
    ("PASS", "Review passed"),
    ("FAIL", "Review failed"),
    ("OUT", "Not delivered and deadline exceeded"),
]

WORKFLOW_REVIEW_STATUS = [
    ("DELIV", "Delivered but not yet reviewed"),
    ("PASS", "Review passed"),
    ("FAIL", "Review failed"),
    ("OUT", "Not delivered and deadline exceeded"),
]

# after this step the delay is running
SECTOR_REGULATION_WORKFLOW_TRIGGER_EVENT = [
    ("NONE", "None"),
    ("NOTIF_DATE", "Notification Date"),
    ("DETECT_DATE", "Detection Date"),
    ("PREV_WORK", "Previous Workflow"),
]

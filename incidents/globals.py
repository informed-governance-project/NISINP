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

EMAIL_TYPES = [
    ("PRELI", "Preliminary notification"),
    ("FINAL", "Final notification"),
    ("ADD", "Additional notification"),
    ("REMIND", "Reminder : final notification not done"),
]

# The variables to use in the email template in the admin interface, and the corresponding attribute
INCIDENT_EMAIL_VARIABLES = [
    ("#PRELIMINARY_NOTIFICATION_DATE#", "preliminary_notification_date"),
]

INCIDENT_STATUS = [
    ("CLOSE", "Closed"),
    ("GOING", "On-going"),
]

REVIEW_STATUS = [
    ("DELIV", "Delivered but not yet reviewed"),
    ("PASS", "Review passed"),
    ("FAIL", "Review failed"),
    ("OUT", "Final notification missing. due date exceeded"),
]

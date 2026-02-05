from django.utils.translation import gettext_lazy as _

STANDARD_ANSWER_REVIEW_STATUS = [
    ("UNDE", _("Unsubmitted")),
    ("DELIV", _("Under review")),
    ("PASS", _("Passed")),
    ("PASSM", _("Passed and sent")),
    ("FAIL", _("Revision required")),
    ("FAILM", _("Revision required and sent")),
]

SO_EMAIL_VARIABLES = [
    ("#SO_REFERENCE#", "group_id"),
]

ALLOWED_SORT_FIELDS = {
    "status": "status",
    "last_update": "last_update",
    "submit_date": "submit_date",
    "identifier": "group__group_id",
    "framework": "standard__translations__label",
    "company_name": "creator_company_name",
    "creator": "creator_name",
    "sectors": "sectors__translations__name",
    "year": "year_of_submission",
    "reviewed_percentage": "reviewed_percentage",
}

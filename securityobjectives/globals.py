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
    "status": {
        "field": "status",
        "type": "string",
    },
    "last_update": {
        "field": "last_update",
        "type": "datetime",
    },
    "submit_date": {
        "field": "submit_date",
        "type": "datetime",
    },
    "identifier": {
        "field": "group__group_id",
        "type": "string",
    },
    "framework": {
        "field": "standard__translations__label",
        "type": "string",
    },
    "company_name": {
        "field": "creator_company_name",
        "type": "string",
    },
    "creator": {
        "field": "creator_name",
        "type": "string",
    },
    "sectors": {
        "field": "sectors__translations__name",
        "type": "string",
    },
    "year": {
        "field": "year_of_submission",
        "type": "number",
    },
    "reviewed_percentage": {
        "field": "reviewed_percentage",
        "type": "number",
    },
}

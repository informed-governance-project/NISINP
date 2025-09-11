from django.utils.translation import gettext_lazy as _

STANDARD_ANSWER_REVIEW_STATUS = [
    ("UNDE", _("Unsubmitted")),
    ("DELIV", _("Under review")),
    ("PASS", _("Passed")),
    ("PASSM", _("Passed and sent")),
    ("FAIL", _("Revision required")),
    ("FAILM", _("Revision required and sent")),
]

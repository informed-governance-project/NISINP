from django.utils.translation import gettext_lazy as _

RISK_TREATMENT = [
    ("REDUC", _("Reduction")),
    ("DENIE", _("Deny")),
    ("ACCEP", _("Acceptation")),
    ("SHARE", _("Shared")),
    ("UNTRE", _("Untreated")),
]

SECTOR_LEGEND = _("Sector average")

SO_COLOR_PALETTE = [
    (0, "#F8696B"),
    (0.5, "#FA9473"),
    (1, "#FCBF7B"),
    (1.5, "#FFEB84"),
    (2, "#CCDD82"),
    (2.5, "#98CE7F"),
    (3, "#63BE7B"),
]

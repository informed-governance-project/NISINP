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
    (0, "#ED2939"),
    (1, "#FFC000"),
    (2, "#DDE96D"),
    (3, "#00B050"),
]

CHARTS_COLOR_PALETTE = [
    ("#023255", "#0063B2"),
    ("#EF7D00", "#F3BC3E"),
    ("#00827D", "#00B796"),
]

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

TRANSLATIONS_CONTEXT = {
    "domain": _("Domain"),
    "evolution": _("Evolution"),
    "sector_average": _("Sector average"),
    "contact": _("Contact"),
    "downward": _("Downward"),
    "stable": _("Stable"),
    "upward": _("Upward"),
    "sector_ranking": _("Sector ranking"),
    "sector_scores": _("Sector scores"),
    "operator_scores": _("Operator scores"),
    "objective": _("Objective"),
    "id": _("ID"),
    "asset": _("Asset"),
    "threat": _("Threat"),
    "vulnerability": _("Vulnerability"),
    "current_risk_max": _("Current risk (max)"),
    "residual_risk": _("Residual risk"),
    "treatment": _("Treatment"),
    "year": _("Year"),
    "treated_risks": _("Treated Risks"),
    "untreated_risks": _("Untreated Risks"),
    "avg_treated_current_risks": _("Average treated current risks"),
    "high_risks": _("High risks"),
    "avg_high_risks": _("Average high risks"),
    "avg_residual_risks": _("Average residual risks"),
    "reduced_risks": _("Reduced risks"),
    "rejected_risks": _("Rejected risks"),
    "accepted_risks": _("Accepted risks"),
    "shared_risks": _("Shared risks"),
}

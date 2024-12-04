import uuid

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from parler.models import TranslatableModel, TranslatedFields

from .globals import RISK_TREATMENT


# Store the JSON
class CompanyReporting(models.Model):
    company = models.ForeignKey(
        "governanceplatform.Company",
        on_delete=models.CASCADE,
        verbose_name=_("Company"),
    )
    timestamp = models.DateTimeField(verbose_name=_("Timestamp"), default=timezone.now)


# Store the statistic by sector, should be updated each time a company from the sector changed
class SectorStatistic(models.Model):
    sector = models.ForeignKey(
        "governanceplatform.Sector",
        on_delete=models.CASCADE,
        verbose_name=_("Sector"),
    )
    timestamp = models.DateTimeField(verbose_name=_("Timestamp"), default=timezone.now)
    high_risk_average = models.FloatField(
        verbose_name=_("Average high risk"),
    )
    risk_average = models.FloatField(
        verbose_name=_("High risk"),
    )

    class Meta:
        verbose_name_plural = _("Sector stats")
        verbose_name = _("Sector stat")


# store asset
class AssetData(TranslatableModel):
    translations = TranslatedFields(
        name=models.CharField(
            verbose_name=_("Name"),
            max_length=255,
            blank=True,
            default=None,
            null=True,
        ),
    )
    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        verbose_name=_("uuid"),
    )

    class Meta:
        verbose_name_plural = _("Asset")
        verbose_name = _("Assets")


# store Vulnerability
class VulnerabilityData(TranslatableModel):
    translations = TranslatedFields(
        name=models.CharField(
            verbose_name=_("Name"),
            max_length=255,
            blank=True,
            default=None,
            null=True,
        ),
    )
    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        verbose_name=_("uuid"),
    )

    class Meta:
        verbose_name_plural = _("Vulnerabilities")
        verbose_name = _("Vulnerability")


# store Threat
class ThreatData(TranslatableModel):
    translations = TranslatedFields(
        name=models.CharField(
            verbose_name=_("Name"),
            max_length=255,
            blank=True,
            default=None,
            null=True,
        ),
    )
    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        verbose_name=_("uuid"),
    )

    class Meta:
        verbose_name_plural = _("Threats")
        verbose_name = _("Threat")


# Store the stat for each service in a risk analysis
class ServiceStat(models.Model):
    service = models.ForeignKey(
        AssetData,
        on_delete=models.CASCADE,
        verbose_name=_("Asset"),
    )

    company_reporting = models.ForeignKey(
        CompanyReporting,
        on_delete=models.CASCADE,
        verbose_name=_("Risk Analysis"),
    )

    total_risks = models.FloatField(verbose_name=_("Total of all risks"), default=0)

    total_untreated_risks = models.FloatField(
        verbose_name=_("Total of untreated risks"), default=0
    )

    total_treated_risks = models.FloatField(
        verbose_name=_("Total of treated risks"), default=0
    )

    total_reduced_risks = models.FloatField(
        verbose_name=_("Total of reduced risks"), default=0
    )

    total_denied_risks = models.FloatField(
        verbose_name=_("Total of denied risks"), default=0
    )

    total_accepted_risks = models.FloatField(
        verbose_name=_("Total of accepted risks"), default=0
    )

    total_shared_risks = models.FloatField(
        verbose_name=_("Total of shared risks"), default=0
    )

    total_high_risks_treated = models.FloatField(
        verbose_name=_("Total high risks treated"), default=0
    )

    avg_high_risk_treated = models.FloatField(
        verbose_name=_("Average high risks treated"), default=0
    )

    avg_current_risks = models.FloatField(
        verbose_name=_("Average of current risks"), default=0
    )

    avg_residual_risks = models.FloatField(
        verbose_name=_("Average of residual risks"), default=0
    )

    class Meta:
        verbose_name_plural = _("Risk analysis stats")
        verbose_name = _("Risk analysis stat")


# Store the risk data
class RiskData(models.Model):
    uuid = models.UUIDField(
        default=uuid.uuid4,
        verbose_name=_("uuid"),
    )
    service = models.ForeignKey(
        ServiceStat,
        on_delete=models.CASCADE,
        verbose_name=_("Service"),
    )
    asset = models.ForeignKey(
        AssetData,
        on_delete=models.CASCADE,
        verbose_name=_("Asset"),
    )
    threat = models.ForeignKey(
        ThreatData,
        on_delete=models.CASCADE,
        verbose_name=_("Threat"),
    )
    threat_value = models.FloatField(
        verbose_name=_("Threat value"),
    )
    vulnerability = models.ForeignKey(
        VulnerabilityData,
        on_delete=models.CASCADE,
        verbose_name=_("Vulnerability"),
    )
    vulnerability_value = models.FloatField(
        verbose_name=_("Vulnerability value"),
    )
    residual_risk_level_value = models.FloatField(
        verbose_name=_("Residual risk level value"),
        default=-1,
    )
    risk_treatment = models.CharField(
        max_length=5,
        verbose_name=_("Risk treatment"),
        choices=RISK_TREATMENT,
        blank=False,
        default=RISK_TREATMENT[1][0],
    )
    max_risk = models.FloatField(
        verbose_name=_("Maximum risk"),
        default=-1,
    )
    risk_c = models.FloatField(
        verbose_name=_("Confidentility risk"),
        default=-1,
    )
    risk_i = models.FloatField(
        verbose_name=_("Integrity risk"),
        default=-1,
    )
    risk_a = models.FloatField(
        verbose_name=_("Availability risk"),
        default=-1,
    )
    impact_c = models.FloatField(
        verbose_name=_("Confidentility impact"),
        default=-1,
    )
    impact_i = models.FloatField(
        verbose_name=_("Integrity impact"),
        default=-1,
    )
    impact_a = models.FloatField(
        verbose_name=_("Availability impact"),
        default=-1,
    )
    recommendations = models.ManyToManyField(
        "RecommendationData", verbose_name=_("recommendations")
    )

    class Meta:
        verbose_name_plural = _("Risks")
        verbose_name = _("Risk")


# Store the recommendation data
class RecommendationData(models.Model):
    code = models.CharField(
        max_length=255,
        verbose_name=_("Recommendation name"),
    )
    description = models.TextField(verbose_name=_("Recommendation description"))

    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        verbose_name=_("uuid"),
    )
    status = models.BooleanField(
        default=False, verbose_name=_("Status of the recommendation")
    )
    due_date = models.DateTimeField(verbose_name=_("Due date"), null=True)

    class Meta:
        verbose_name_plural = _("Recommendations")
        verbose_name = _("Recommendation")


# store the configuration
class SectorReportConfiguration(models.Model):
    sector = models.ForeignKey(
        "governanceplatform.Sector",
        on_delete=models.CASCADE,
        verbose_name=_("Sector"),
    )
    threshold_for_high_risk = models.FloatField(
        verbose_name=_("High risk rate threshold"),
    )
    number_of_year_considered = models.PositiveSmallIntegerField(
        verbose_name=_("Number of year considered"),
    )
    high_risk_number_for_top = models.PositiveSmallIntegerField(
        verbose_name=_("Number of high risks for top"),
    )
    threat_number_for_top = models.PositiveSmallIntegerField(
        verbose_name=_("Number of threats for top"),
    )
    vulnerability_number_for_top = models.PositiveSmallIntegerField(
        verbose_name=_("Number of vulnerabilities for top"),
    )
    asset_number_for_top = models.PositiveSmallIntegerField(
        verbose_name=_("Number of assets for top"),
    )
    asset_recommendation_for_top = models.PositiveSmallIntegerField(
        verbose_name=_("Number of recommendations for top"),
    )

    class Meta:
        verbose_name_plural = _("Configurations")
        verbose_name = _("Configuration")


# recommendation for observation
class ObservationRecommendation(TranslatableModel):
    translations = TranslatedFields(
        description=models.TextField(
            verbose_name=_("description"),
            blank=True,
            default=None,
            null=True,
        ),
    )
    code = models.CharField(
        max_length=255,
        verbose_name=_("Recommendation name"),
    )
    is_generic = models.BooleanField(default=False, verbose_name=_("Is Generic ?"))
    sectors = models.ManyToManyField(
        "governanceplatform.Company",
        verbose_name=_("Sectors"),
    )
    creation_date = models.DateTimeField(
        verbose_name=_("Creation date"), default=timezone.now
    )

    class Meta:
        verbose_name_plural = _("Recommendations for observation")
        verbose_name = _("Recommendation for observation")


# observation of regulator
class Observation(models.Model):
    company_reporting = models.ForeignKey(
        CompanyReporting,
        on_delete=models.CASCADE,
        verbose_name=_("Risk Analysis"),
    )
    observation_recommendations = models.ManyToManyField(
        ObservationRecommendation,
        verbose_name=_("Observation recommendations"),
    )

    class Meta:
        verbose_name_plural = _("Observations")
        verbose_name = _("Observation")

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from parler.models import TranslatableModel, TranslatedFields
from .globals import RISK_TREATMENT


# Store the JSON
class RiskAnalysisJson(models.Model):
    data = models.JSONField(
        verbose_name=_("Data")
    )
    company = models.ForeignKey(
        "governanceplatform.Company",
        on_delete=models.CASCADE,
        verbose_name=_("Company"),
    )
    timestamp = models.DateTimeField(verbose_name=_("Timestamp"), default=timezone.now)


# scales information
class ScaleData(TranslatableModel):
    translations = TranslatedFields(
        name=models.CharField(
            verbose_name=_("Name"),
            max_length=255,
            blank=True,
            default=None,
            null=True,
        ),
    )
    minimum = models.IntegerField(verbose_name=_("Minimum"))
    maximum = models.IntegerField(verbose_name=_("Maximum"))
    risk_analysis = models.ForeignKey(
        RiskAnalysisJson,
        on_delete=models.CASCADE,
        verbose_name=_("Risk Analysis"),
    )


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
        verbose_name_plural = _("Secrtor stats")
        verbose_name = _("Sector stat")


# Store the stat for each service in a risk analysis
class ServiceStat(models.Model):
    service_name = models.CharField(
        verbose_name=_("Service name"),
        max_length=255,
    )
    risk_analysis = models.ForeignKey(
        RiskAnalysisJson,
        on_delete=models.CASCADE,
        verbose_name=_("Risk Analysis"),
    )
    treshold_for_high_risk = models.FloatField(
        verbose_name=_("High risk rate treshold"),
    )
    high_risk_rate = models.FloatField(
        verbose_name=_("High risk rate"),
    )
    high_risk_average = models.FloatField(
        verbose_name=_("Average high risk"),
    )

    class Meta:
        verbose_name_plural = _("Risk analysis stats")
        verbose_name = _("Risk analysis stat")


# store asset
class AssetData(models.Model):
    name = models.CharField(
        max_length=255,
        verbose_name=_("Asset name"),
    )
    asset_type_uuid = models.CharField(
        max_length=32,
        verbose_name=_("Asset Type uuid"),
    )
    impacts = models.ManyToManyField(
        ScaleData, through="AssetScale", verbose_name=_("Scales value")
    )

    class Meta:
        verbose_name_plural = _("Asset")
        verbose_name = _("Assets")


# impact for assets
class AssetScale(models.Model):
    asset = models.ForeignKey(
        AssetData,
        on_delete=models.CASCADE,
        verbose_name=_("Asset"),
    )
    scale = models.ForeignKey(
        ScaleData,
        on_delete=models.CASCADE,
        verbose_name=_("Scale"),
    )
    value = models.FloatField(
        verbose_name=_("Value"),
    )


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
    uuid = models.CharField(
        max_length=32,
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
    uuid = models.CharField(
        max_length=32,
        verbose_name=_("uuid"),
    )

    class Meta:
        verbose_name_plural = _("Threats")
        verbose_name = _("Threat")


# Store the risk data
class RiskData(models.Model):
    service = models.ForeignKey(
        ServiceStat,
        on_delete=models.CASCADE,
        verbose_name=_("Service"),
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
    risk_level_value = models.FloatField(
        verbose_name=_("Risk level value"),
    )
    residual_risk_level_value = models.FloatField(
        verbose_name=_("Residual risk level value"),
    )
    risk_treatment = models.CharField(
        max_length=5,
        verbose_name=_("Risk treatment"),
        choices=RISK_TREATMENT,
        blank=False,
        default=RISK_TREATMENT[1][0],
    )

    class Meta:
        verbose_name_plural = _("Risks")
        verbose_name = _("Risk")


# Store the recommendation data
class RecommendationData(models.Model):
    name = models.CharField(
        max_length=255,
        verbose_name=_("Recommendation name"),
    )
    description = models.TextField(
        verbose_name=_("Recommendation description")
    )

    class Meta:
        verbose_name_plural = _("Recommendations")
        verbose_name = _("Recommendation")

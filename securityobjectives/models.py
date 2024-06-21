from django.db import models
from parler.models import TranslatableModel, TranslatedFields
from django.utils.translation import gettext_lazy as _


# Maturity level : define a matury (e.g. sophisticated)
class MaturityLevel(TranslatableModel):
    translations = TranslatedFields(
        label=models.CharField(max_length=255, blank=True, default=None, null=True),
    )


# Domain : To categorize the security objectives
class Domain(TranslatableModel):
    translations = TranslatedFields(
        label=models.CharField(max_length=255, blank=True, default=None, null=True),
    )
    position = models.IntegerField(default=0)


# Standard : A group of security objectives
class Standard(TranslatableModel):
    translations = TranslatedFields(
        label=models.CharField(max_length=255, blank=True, default=None, null=True),
        description=models.TextField(),
    )
    position = models.IntegerField(default=0)


# SecurityObejctive (SO)
class SecurityMeasure(TranslatableModel):
    translations = TranslatedFields(
        description=models.TextField(),
        evidence=models.TextField(),
    )
    position = models.IntegerField(default=0)


# SecurityObejctive (SO)
class SecurityObejctive(TranslatableModel):
    translations = TranslatedFields(
        objective=models.CharField(max_length=255, blank=True, default=None, null=True),
        description=models.TextField(),
    )
    position = models.IntegerField(default=0)
    unique_code = models.CharField(max_length=255, blank=True, default=None, null=True),
    # when we want to delete a SO we need to check if it has been answered in yes, history instead of delete
    is_archived = models.BooleanField(
        default=False, verbose_name=_("is archived")
    )
    domain = models.ForeignKey(
        Domain,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
        related_name="domain",
    )
    standards = models.ManyToManyField(Standard)
    security_measures = models.ManyToManyField(SecurityMeasure, through="Measure")


# link between security measure, SO and maturity
class Measure(models.Model):
    security_measure = models.ForeignKey(SecurityMeasure, on_delete=models.CASCADE)
    security_objective = models.ForeignKey(SecurityObejctive, on_delete=models.CASCADE)
    maturity_level = models.ForeignKey(MaturityLevel, on_delete=models.SET_NULL, null=True)

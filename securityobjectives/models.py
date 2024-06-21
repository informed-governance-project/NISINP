from django.db import models
from django.contrib import admin
from parler.models import TranslatableModel, TranslatedFields
from django.utils.translation import gettext_lazy as _
from django.db.models import Deferrable


# Maturity level : define a matury (e.g. sophisticated)
class MaturityLevel(TranslatableModel):
    translations = TranslatedFields(
        label=models.CharField(max_length=255, blank=True, default=None, null=True),
    )

    def __str__(self):
        return self.label if self.label is not None else ""


# Domain : To categorize the security objectives
class Domain(TranslatableModel):
    translations = TranslatedFields(
        label=models.CharField(max_length=255, blank=True, default=None, null=True),
    )
    position = models.IntegerField(default=0)

    def __str__(self):
        return self.label if self.label is not None else ""


# Standard : A group of security objectives
class Standard(TranslatableModel):
    translations = TranslatedFields(
        label=models.CharField(max_length=255, blank=True, default=None, null=True),
        description=models.TextField(),
    )
    regulator = models.ForeignKey("governanceplatform.regulator", on_delete=models.CASCADE)
    regulation = models.ForeignKey("governanceplatform.regulation", on_delete=models.CASCADE)

    def __str__(self):
        return self.label if self.label is not None else ""


# SecurityObejctive (SO)
class SecurityObejctive(TranslatableModel, models.Model):
    translations = TranslatedFields(
        objective=models.CharField(max_length=255, blank=True, default=None, null=True),
        description=models.TextField(),
    )
    position = models.IntegerField(default=0)
    unique_code = models.CharField(max_length=255, blank=True, default=None, null=True)
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

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["unique_code"],
                name="Unique_unique_code",
                deferrable=Deferrable.DEFERRED,
            ),
        ]

    def __str__(self):
        return self.objective if self.objective is not None else ""

    @admin.display(description="standards")
    def get_standards(self):
        standards = []
        for standard in self.standards.all().distinct():
            standards.append(standard.label)

        return standards


# link between security measure, SO and maturity
class SecurityMeasure(TranslatableModel):
    security_objective = models.ForeignKey(SecurityObejctive, on_delete=models.CASCADE)
    maturity_level = models.ForeignKey(MaturityLevel, on_delete=models.SET_NULL, null=True)
    translations = TranslatedFields(
        description=models.TextField(),
        evidence=models.TextField(),
    )
    position = models.IntegerField(default=0)

    def __str__(self):
        return self.description if self.description is not None else ""

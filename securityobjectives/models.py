from django.db import models
from django.db.models import Deferrable
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from parler.models import TranslatableModel, TranslatedFields

from incidents.globals import REVIEW_STATUS


# Maturity level : define a matury (e.g. sophisticated)
class MaturityLevel(TranslatableModel):
    translations = TranslatedFields(
        label=models.CharField(max_length=255, blank=True, default=None, null=True),
    )
    level = models.IntegerField(default=0)

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


# SecurityObjective (SO)
class SecurityObjective(TranslatableModel, models.Model):
    translations = TranslatedFields(
        objective=models.CharField(max_length=255, blank=True, default=None, null=True),
        description=models.TextField(),
    )
    unique_code = models.CharField(max_length=255, blank=True, default=None, null=True)
    # when we want to delete a SO we need to check if it has been answered if yes, archived instead of delete
    is_archived = models.BooleanField(default=False, verbose_name=_("is archived"))
    domain = models.ForeignKey(
        Domain,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
        related_name="securityobjective",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["unique_code"],
                name="Unique_unique_code",
                deferrable=Deferrable.DEFERRED,
            ),
        ]

    def __str__(self):
        objective_translation = self.safe_translation_getter(
            "objective", any_language=True
        )
        return f"{self.unique_code}:{objective_translation}" or ""


# Email sent from regulator to operator
class SecurityObjectiveEmail(TranslatableModel, models.Model):
    translations = TranslatedFields(
        subject=models.CharField(
            verbose_name=_("Subject"),
            max_length=255,
        ),
        content=models.TextField(verbose_name=_("Content")),
    )
    name = models.CharField(verbose_name=_("Name"), max_length=255)
    # name of the regulator who create the object
    creator_name = models.CharField(
        verbose_name=_("Creator name"),
        max_length=255,
        blank=True,
        default=None,
        null=True,
    )
    creator = models.ForeignKey(
        "governanceplatform.regulator",
        verbose_name=_("Creator"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
    )

    def __str__(self):
        return self.name or ""

    class Meta:
        verbose_name_plural = _("Email templates")
        verbose_name = _("Email template")


# Standard : A group of security objectives
class Standard(TranslatableModel):
    translations = TranslatedFields(
        label=models.CharField(max_length=255, blank=True, default=None, null=True),
        description=models.TextField(),
    )
    regulator = models.ForeignKey(
        "governanceplatform.regulator", on_delete=models.CASCADE
    )
    regulation = models.ForeignKey(
        "governanceplatform.regulation", on_delete=models.CASCADE
    )
    security_objectives = models.ManyToManyField(
        SecurityObjective, through="SecurityObjectivesInStandard"
    )
    # email
    submission_email = models.ForeignKey(
        SecurityObjectiveEmail,
        verbose_name=_("Submission e-mail"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
        related_name="security_objective_submission_email",
    )
    security_objective_status_changed_email = models.ForeignKey(
        SecurityObjectiveEmail,
        verbose_name=_("Email for status change"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
        related_name="security_objective_status_changed_email",
    )

    def __str__(self):
        label_translation = self.safe_translation_getter("label", any_language=True)
        return label_translation or ""


class SecurityObjectivesInStandard(models.Model):
    security_objective = models.ForeignKey(
        SecurityObjective,
        on_delete=models.CASCADE,
    )
    standard = models.ForeignKey(
        Standard,
        on_delete=models.CASCADE,
    )
    position = models.IntegerField(default=0)


# link between security measure, SO and maturity
class SecurityMeasure(TranslatableModel):
    security_objective = models.ForeignKey(SecurityObjective, on_delete=models.CASCADE)
    maturity_level = models.ForeignKey(
        MaturityLevel, on_delete=models.SET_NULL, null=True
    )
    translations = TranslatedFields(
        description=models.TextField(),
        evidence=models.TextField(),
    )
    position = models.IntegerField(default=0)
    # when we want to delete a Security Measure we need to check if it has been answered if yes, archived instead of delete
    is_archived = models.BooleanField(default=False, verbose_name=_("is archived"))

    def __str__(self):
        return self.description if self.description is not None else ""


# The answers of the operator
class StandardAnswer(models.Model):
    standard = models.ForeignKey(
        Standard,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
        related_name="standardanswer",
    )
    last_update = models.DateTimeField(default=timezone.now)
    submit_date = models.DateTimeField(blank=True, default=None, null=True)
    status = models.CharField(
        max_length=5,
        choices=REVIEW_STATUS,
        blank=False,
        default=REVIEW_STATUS[0][0],
        verbose_name=_("Status"),
    )
    submitter_user = models.ForeignKey(
        "governanceplatform.user", on_delete=models.SET_NULL, null=True
    )
    submitter_company = models.ForeignKey(
        "governanceplatform.company", on_delete=models.SET_NULL, null=True
    )
    # to display in case we delete the user or the company
    creator_name = models.CharField(max_length=255, blank=True, default=None, null=True)
    creator_company_name = models.CharField(
        max_length=255, blank=True, default=None, null=True
    )
    # the year for the one
    year_of_submission = models.PositiveIntegerField()


# the answer of the operator by SM
class SecurityMeasureAnswer(models.Model):
    security_measure_notification_date = models.DateTimeField(default=timezone.now)
    standard_answer = models.ForeignKey(
        StandardAnswer,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        default=None,
        related_name="securitymeasureanswers",
    )
    security_measure = models.ForeignKey(
        SecurityMeasure,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        default=None,
        related_name="securitymeasureanswers",
    )
    comment = models.TextField()
    is_implemented = models.BooleanField(default=False, verbose_name=_("Implemented"))
    review_comment = models.TextField()


# SO Status set by regulator
class SecurityObjectiveStatus(models.Model):
    standard_answer = models.ForeignKey(
        StandardAnswer,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        default=None,
    )
    security_objective = models.ForeignKey(
        SecurityObjective,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        default=None,
    )
    status = models.CharField(
        choices=[
            ("NOT_REVIEWED", _("Not reviewed")),
            ("PASS", _("Pass")),
            ("FAIL", _("Fail")),
        ],
        blank=False,
        default=REVIEW_STATUS[0][0],
        verbose_name=_("Status"),
    )

    score = models.DecimalField(
        default=0,
        max_digits=4,
        decimal_places=2,
    )

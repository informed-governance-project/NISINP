from django.db import models
from django.db.models import Deferrable
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from parler.models import TranslatableModel, TranslatedFields

from .globals import STANDARD_ANSWER_REVIEW_STATUS


# Maturity level : define a matury (e.g. sophisticated)
class MaturityLevel(TranslatableModel):
    translations = TranslatedFields(
        label=models.CharField(max_length=255, blank=True, default=None, null=True),
    )
    level = models.IntegerField(default=0)
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
        return self.label if self.label is not None else ""


# Domain : To categorize the security objectives
class Domain(TranslatableModel):
    translations = TranslatedFields(
        label=models.CharField(max_length=255, blank=True, default=None, null=True),
    )
    position = models.IntegerField(default=0)
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

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["unique_code", "creator"],
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
    priority = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["security_objective", "standard"],
                name="unique_security_objective_per_standard",
            ),
        ]


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
        choices=STANDARD_ANSWER_REVIEW_STATUS,
        blank=False,
        default=STANDARD_ANSWER_REVIEW_STATUS[0][0],
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
    sectors = models.ManyToManyField(
        "governanceplatform.sector", verbose_name=_("Sectors")
    )
    review_comment = models.TextField(
        blank=True, default=None, null=True, verbose_name=_("Review comment")
    )
    deadline = models.DateTimeField(
        blank=True, default=None, null=True, verbose_name=_("Deadline")
    )

    def get_root_sectors(self):
        return list({sector.parent for sector in self.sectors.all()})

    def get_no_childrens_sectors(self):
        return list(self.sectors.filter(parent__isnull=True))


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
    justification = models.TextField()
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
        default="NOT_REVIEWED",
        verbose_name=_("Status"),
    )

    score = models.DecimalField(
        default=0,
        max_digits=4,
        decimal_places=2,
    )

    actions = models.TextField(
        blank=True,
        default=None,
        null=True,
        verbose_name=_("Planned Measures"),
    )

    is_completely_filled_out = models.BooleanField(
        default=False, verbose_name=_("It is completely filled out")
    )


class LogStandardAnswer(models.Model):
    user = models.ForeignKey(
        "governanceplatform.User",
        on_delete=models.SET_NULL,
        verbose_name=_("User"),
        null=True,
    )
    timestamp = models.DateTimeField(verbose_name=_("Timestamp"), default=timezone.now)
    # save full name in case of the user is deleted to keep the name
    user_full_name = models.CharField(max_length=250, verbose_name=_("User full name"))
    role = models.CharField(max_length=250, verbose_name=_("Role"))
    entity_name = models.CharField(max_length=250, verbose_name=_("Entity name"))
    standard_answer = models.ForeignKey(
        StandardAnswer,
        on_delete=models.CASCADE,
        null=True,
        default=None,
    )
    action = models.CharField(max_length=10, verbose_name=_("Action performed"))

    def save(self, *args, **kwargs):
        self.user_full_name = self.user.get_full_name()
        super().save(*args, **kwargs)

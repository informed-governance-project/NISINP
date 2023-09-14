from datetime import date

from django.contrib import admin
from django.db import models
from django.utils.translation import gettext_lazy as _
from parler.models import TranslatableModel, TranslatedFields

from .globals import EMAIL_TYPES, QUESTION_TYPES


# impacts of the incident, they are linked to sector
class Impact(TranslatableModel):
    """Defines an impact."""

    translations = TranslatedFields(label=models.TextField())
    is_generic_impact = models.BooleanField(
        default=False, verbose_name=_("Generic Impact")
    )

    def __str__(self):
        return self.label


# answers for the question
class PredifinedAnswer(TranslatableModel):
    translations = TranslatedFields(predifined_answer=models.TextField())
    allowed_additional_answer = models.BooleanField(
        default=False, verbose_name=_("Additional Answer")
    )

    def __str__(self):
        return self.predifined_answer


# category for the question (to order)
class QuestionCategory(TranslatableModel):
    translations = TranslatedFields(
        label=models.CharField(max_length=255, blank=True, default=None, null=True)
    )
    position = models.IntegerField()

    def __str__(self):
        return self.label

    class Meta:
        verbose_name = _("Question Category")
        verbose_name_plural = _("Question Categories")


# questions asked during the Incident notification process
class Question(TranslatableModel):
    question_type = models.CharField(
        max_length=10, choices=QUESTION_TYPES, blank=False, default=QUESTION_TYPES[0][0]
    )  # MULTI, FREETEXT, DATE,
    is_mandatory = models.BooleanField(default=False, verbose_name=_("Mandatory"))
    is_preliminary = models.BooleanField(default=False, verbose_name=_("Preliminary"))
    translations = TranslatedFields(
        label=models.TextField(),
        tooltip=models.CharField(max_length=255, blank=True, default=None, null=True),
    )
    predifined_answers = models.ManyToManyField(PredifinedAnswer, blank=True)
    position = models.IntegerField()
    category = models.ForeignKey(
        QuestionCategory, on_delete=models.SET_NULL, default=None, null=True, blank=True
    )

    @admin.display(description="Predifined Answer")
    def get_predifined_answers(self):
        return [
            predifined_answer.predifined_answer
            for predifined_answer in self.predifined_answers.all()
        ]

    def __str__(self):
        return self.label


# type of regulation
class RegulationType(TranslatableModel):
    translations = TranslatedFields(
        label=models.CharField(max_length=255, blank=True, default=None, null=True)
    )

    def __str__(self):
        return self.label


# incident
class Incident(models.Model):
    # XXXX-SSS-SSS-NNNN-YYYY
    incident_id = models.CharField(max_length=22, verbose_name=_("Incident identifier"))
    preliminary_notification_date = models.DateField(default=date.today)
    company_name = models.CharField(max_length=100, verbose_name=_("Company name"))
    company = models.ForeignKey(
        "governanceplatform.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
    )
    # we allo to store user in case he is registered
    contact_user = models.ForeignKey(
        "governanceplatform.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
    )
    contact_lastname = models.CharField(
        max_length=100, verbose_name=_("contact lastname")
    )
    contact_firstname = models.CharField(
        max_length=100, verbose_name=_("contact firstname")
    )
    contact_title = models.CharField(max_length=100, verbose_name=_("contact title"))
    contact_email = models.CharField(max_length=100, verbose_name=_("contact email"))
    contact_telephone = models.CharField(
        max_length=100, verbose_name=_("contact telephone")
    )
    # technical contact
    technical_lastname = models.CharField(
        max_length=100, verbose_name=_("technical lastname")
    )
    technical_firstname = models.CharField(
        max_length=100, verbose_name=_("technical firstname")
    )
    technical_title = models.CharField(
        max_length=100, verbose_name=_("technical title")
    )
    technical_email = models.CharField(
        max_length=100, verbose_name=_("technical email")
    )
    technical_telephone = models.CharField(
        max_length=100, verbose_name=_("technical telephone")
    )

    incident_reference = models.CharField(max_length=255)
    complaint_reference = models.CharField(max_length=255)

    affected_services = models.ManyToManyField("governanceplatform.Services")
    regulations = models.ManyToManyField(RegulationType)
    final_notification_date = models.DateField(null=True, blank=True)
    impacts = models.ManyToManyField(Impact, default=None)
    is_significative_impact = models.BooleanField(
        default=False, verbose_name=_("Significative impact")
    )


# answers
class Answer(models.Model):
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    answer = models.TextField(null=True, blank=True)
    PredifinedAnswer = models.ManyToManyField(PredifinedAnswer, blank=True)


# Email sent from regulator to operator
class Email(TranslatableModel):
    email_type = models.CharField(
        max_length=10, choices=EMAIL_TYPES, blank=False, default=EMAIL_TYPES[0][0]
    )
    translations = TranslatedFields(
        subject=models.CharField(max_length=255, blank=True, default=None, null=True),
        content=models.TextField(),
    )
    # for the reminder at day 12 and 16
    days_before_send = models.IntegerField(blank=True, null=True, default=0)

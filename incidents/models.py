from datetime import date

from django.contrib import admin
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from parler.models import TranslatableModel, TranslatedFields

from .globals import EMAIL_TYPES, INCIDENT_STATUS, QUESTION_TYPES, REVIEW_STATUS, WORKFLOW_REVIEW_STATUS


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
class PredefinedAnswer(TranslatableModel):
    translations = TranslatedFields(predefined_answer=models.TextField())
    position = models.IntegerField(blank=True, default=0, null=True)

    def __str__(self):
        return self.predefined_answer


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
    translations = TranslatedFields(
        label=models.TextField(),
        tooltip=models.TextField(blank=True, null=True),
    )
    predefined_answers = models.ManyToManyField(PredefinedAnswer, blank=True)
    position = models.IntegerField()
    category = models.ForeignKey(
        QuestionCategory, on_delete=models.SET_NULL, default=None, null=True, blank=True
    )

    @admin.display(description="Predefined Answer")
    def get_predefined_answers(self):
        return [
            predefined_answer.predefined_answer
            for predefined_answer in self.predefined_answers.all()
        ]

    def __str__(self):
        return self.label


# Workflow for each sector_regulation, N workflow for 1 reglementation,
# 1 Workflow for N recommendation ?
class Workflow(TranslatableModel):
    translations = TranslatedFields(
        name=models.CharField(max_length=255, blank=True, default=None, null=True)
    )
    questions = models.ManyToManyField(Question)

    def __str__(self):
        return self.name


# link between a regulation and a regulator,
# a regulator can only create a sector_regulation for the regulation the
# admin platform has designated him
class SectorRegulation(TranslatableModel):
    translations = TranslatedFields(
        # for exemple NIS for enery sector
        name=models.CharField(max_length=255, blank=True, default=None, null=True)
    )
    regulation = models.ForeignKey(
        "governanceplatform.Regulation", on_delete=models.CASCADE
    )
    regulator = models.ForeignKey(
        "governanceplatform.Regulator", on_delete=models.CASCADE
    )
    workflows = models.ManyToManyField(Workflow, through="SectorRegulationWorkflow")

    sectors = models.ManyToManyField("governanceplatform.Sector", default=None, blank=True)
    impacts = models.ManyToManyField(Impact, default=None, blank=True)

    def __str__(self):
        return self.name


# link between sector regulation and workflows
class SectorRegulationWorkflow(models.Model):
    sector_regulation = models.ForeignKey(
        SectorRegulation, on_delete=models.CASCADE
    )
    workflow = models.ForeignKey(
        Workflow, on_delete=models.CASCADE
    )
    position = models.IntegerField(blank=True, default=0, null=True)


# incident
class Incident(models.Model):
    # XXXX-SSS-SSS-NNNN-YYYY
    incident_id = models.CharField(max_length=22, verbose_name=_("Incident identifier"))
    incident_notification_date = models.DateField(default=date.today)
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

    affected_services = models.ManyToManyField("governanceplatform.Service")
    sector_regulation = models.ForeignKey(
        SectorRegulation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,)
    workflows = models.ManyToManyField(Workflow, through='IncidentWorkflow')
    impacts = models.ManyToManyField(Impact, default=None, )
    is_significative_impact = models.BooleanField(
        default=False, verbose_name=_("Significative impact")
    )

    # notification dispatching
    authorities = models.ManyToManyField(
        "governanceplatform.Regulator", related_name="authorities"
    )

    # status
    review_status = models.CharField(
        max_length=5, choices=REVIEW_STATUS, blank=False, default=REVIEW_STATUS[0][0]
    )
    incident_status = models.CharField(
        max_length=5,
        choices=INCIDENT_STATUS,
        blank=False,
        default=INCIDENT_STATUS[0][0],
    )

    def get_review_status(self):
        return dict(REVIEW_STATUS).get(self.review_status)

    def get_incident_status(self):
        return dict(INCIDENT_STATUS).get(self.incident_status)

    def get_next_step(self):
        current_workflow = IncidentWorkflow.objects.all().filter(
            incident=self,
        ).values_list('workflow')
        regulation = SectorRegulationWorkflow.objects.all().filter(
            sector_regulation=self.sector_regulation,
        ).exclude(workflow__in=current_workflow).order_by("position")
        return regulation[0].workflow

    def get_completed_workflows(self):
        current_workflow = IncidentWorkflow.objects.all().filter(
            incident=self,
        )
        return current_workflow


# link between incident and workflow
class IncidentWorkflow(models.Model):
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE)
    workflow = models.ForeignKey(Workflow, on_delete=models.SET_NULL, null=True)
    # for versionning
    timestamp = models.DateTimeField(default=timezone.now)
    review_status = models.CharField(
        max_length=5, choices=REVIEW_STATUS, blank=False, default=WORKFLOW_REVIEW_STATUS[0][0]
    )


# answers
class Answer(models.Model):
    incident_workflow = models.ForeignKey(IncidentWorkflow, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    answer = models.TextField(null=True, blank=True)
    predefined_answers = models.ManyToManyField(PredefinedAnswer, blank=True)


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

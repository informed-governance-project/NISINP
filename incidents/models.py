from django.contrib import admin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from parler.models import TranslatableModel, TranslatedFields

from .globals import (
    INCIDENT_EMAIL_TRIGGER_EVENT,
    INCIDENT_STATUS,
    QUESTION_TYPES,
    REVIEW_STATUS,
    SECTOR_REGULATION_WORKFLOW_TRIGGER_EVENT,
    WORKFLOW_REVIEW_STATUS,
)


# impacts of the incident, they are linked to sector
class Impact(TranslatableModel):
    """Defines an impact."""

    translations = TranslatedFields(
        label=models.TextField(),
        headline=models.CharField(max_length=255, blank=True, default=None, null=True),
    )
    regulation = models.ForeignKey(
        "governanceplatform.Regulation",
        on_delete=models.CASCADE,
    )
    sectors = models.ManyToManyField(
        "governanceplatform.Sector", default=None, blank=True
    )

    # name of the regulator who create the object
    creator_name = models.CharField(max_length=255, blank=True, default=None, null=True)
    creator = models.ForeignKey(
        "governanceplatform.regulator",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
    )

    def __str__(self):
        return self.label if self.label is not None else ""


# category for the question (to order)
class QuestionCategory(TranslatableModel):
    translations = TranslatedFields(
        label=models.CharField(max_length=255, blank=True, default=None, null=True)
    )
    position = models.IntegerField()

    # name of the regulator who create the object
    creator_name = models.CharField(max_length=255, blank=True, default=None, null=True)
    creator = models.ForeignKey(
        "governanceplatform.regulator",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
    )

    def __str__(self):
        return self.label if self.label is not None else ""

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
    position = models.IntegerField()
    category = models.ForeignKey(
        QuestionCategory, on_delete=models.SET_NULL, default=None, null=True, blank=True
    )

    # name of the regulator who create the object
    creator_name = models.CharField(max_length=255, blank=True, default=None, null=True)
    creator = models.ForeignKey(
        "governanceplatform.regulator",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
    )

    @admin.display(description="Predefined Answers")
    def get_predefined_answers(self):
        return [
            predefined_answer.predefined_answer
            for predefined_answer in self.predefinedanswer_set.all()
        ]

    def __str__(self):
        return self.label if self.label is not None else ""


# answers for the question
class PredefinedAnswer(TranslatableModel):
    translations = TranslatedFields(predefined_answer=models.TextField())
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, default=None, null=True
    )
    position = models.IntegerField(blank=True, default=0, null=True)

    # name of the regulator who create the object
    creator_name = models.CharField(max_length=255, blank=True, default=None, null=True)
    creator = models.ForeignKey(
        "governanceplatform.regulator",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
    )

    def __str__(self):
        return self.predefined_answer if self.predefined_answer is not None else ""

    class Meta:
        verbose_name_plural = "Question - predefined answers"
        verbose_name = "Question - predefined answer"


# Email sent from regulator to operator
class Email(TranslatableModel, models.Model):
    translations = TranslatedFields(
        subject=models.CharField(max_length=255, blank=True, default=None, null=True),
        content=models.TextField(),
    )
    name = models.CharField(max_length=255, blank=True, default=None, null=True)
    # name of the regulator who create the object
    creator_name = models.CharField(max_length=255, blank=True, default=None, null=True)
    creator = models.ForeignKey(
        "governanceplatform.regulator",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
    )

    def __str__(self):
        return self.name if self.name is not None else ""

    class Meta:
        verbose_name_plural = "Email templates"
        verbose_name = "Email template"


# Workflow for each sector_regulation, N workflow for 1 reglementation,
# 1 Workflow for N recommendation ?
class Workflow(TranslatableModel):
    translations = TranslatedFields(
        name=models.CharField(max_length=255, blank=True, default=None, null=True)
    )
    is_impact_needed = models.BooleanField(
        default=False, verbose_name=_("Impacts are needed")
    )
    questions = models.ManyToManyField(Question)

    def __str__(self):
        return self.name if self.name is not None else ""

    class Meta:
        verbose_name_plural = "Incident Reports"
        verbose_name = "Incident report"

    submission_email = models.ForeignKey(
        Email,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
        related_name="submission_email",
    )

    # name of the regulator who create the object
    creator_name = models.CharField(max_length=255, blank=True, default=None, null=True)
    creator = models.ForeignKey(
        "governanceplatform.regulator",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
    )


# link between a regulation and a regulator,
# a regulator can only create a sector_regulation for the regulation the
# admin platform has designated him
class SectorRegulation(TranslatableModel):
    translations = TranslatedFields(
        # for exemple NIS for energy sector
        name=models.CharField(max_length=255, blank=True, default=None, null=True)
    )
    regulation = models.ForeignKey(
        "governanceplatform.Regulation", on_delete=models.CASCADE
    )
    regulator = models.ForeignKey(
        "governanceplatform.Regulator", on_delete=models.CASCADE
    )
    workflows = models.ManyToManyField(Workflow, through="SectorRegulationWorkflow")

    sectors = models.ManyToManyField(
        "governanceplatform.Sector", default=None, blank=True
    )
    is_detection_date_needed = models.BooleanField(
        default=False, verbose_name=_("Detection date needed")
    )
    # email
    opening_email = models.ForeignKey(
        Email,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
        related_name="opening_email",
    )
    closing_email = models.ForeignKey(
        Email,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
        related_name="closing_email",
    )

    class Meta:
        verbose_name_plural = "Incident notification workflows"
        verbose_name = "Incident notification workflow"

    def __str__(self):
        return self.name if self.name is not None else ""


# link between sector regulation and workflows
class SectorRegulationWorkflow(models.Model):
    sector_regulation = models.ForeignKey(SectorRegulation, on_delete=models.CASCADE)
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE)
    position = models.IntegerField(blank=True, default=0, null=True)
    # the delay after the trigger event
    delay_in_hours_before_deadline = models.IntegerField(default=0)
    trigger_event_before_deadline = models.CharField(
        max_length=15,
        choices=SECTOR_REGULATION_WORKFLOW_TRIGGER_EVENT,
        blank=False,
        default=SECTOR_REGULATION_WORKFLOW_TRIGGER_EVENT[0][0],
    )
    emails = models.ManyToManyField(Email, through="SectorRegulationWorkflowEmail")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["sector_regulation", "position"], name="Unique_SectorRegulationWorkflowPosition"
            ),
        ]

    def __str__(self):
        return self.workflow.name if self.workflow is not None else ""


# for emailing during each workflow
class SectorRegulationWorkflowEmail(TranslatableModel):
    translations = TranslatedFields(
        headline=models.CharField(max_length=255, blank=True, default=None, null=True),
    )

    sector_regulation_workflow = models.ForeignKey(
        SectorRegulationWorkflow, on_delete=models.CASCADE
    )
    email = models.ForeignKey(Email, on_delete=models.CASCADE)
    # the trigger event which send the email
    trigger_event = models.CharField(
        max_length=15,
        choices=INCIDENT_EMAIL_TRIGGER_EVENT,
        blank=False,
        default=INCIDENT_EMAIL_TRIGGER_EVENT[0][0],
    )
    # the delay after the trigger event
    delay_in_hours = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = "Emails for Incident notification workflows"
        verbose_name = "Email for Incident notification workflow"

    def __str__(self):
        return self.headline if self.headline is not None else ""

    def regulation(self):
        return self.sector_regulation_workflow.sector_regulation.regulation


# incident
class Incident(models.Model):
    # XXXX-SSS-SSS-NNNN-YYYY
    incident_id = models.CharField(max_length=22, verbose_name=_("Incident identifier"))
    incident_notification_date = models.DateTimeField(default=timezone.now)
    incident_detection_date = models.DateTimeField(blank=True, null=True)
    incident_starting_date = models.DateTimeField(blank=True, null=True)
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
        default=None,
    )
    # keep a trace of selected sectors
    affected_sectors = models.ManyToManyField("governanceplatform.Sector")
    workflows = models.ManyToManyField(Workflow, through="IncidentWorkflow")
    impacts = models.ManyToManyField(
        Impact,
        default=None,
    )
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
        default=INCIDENT_STATUS[1][0],
    )

    def get_next_step(self):
        current_workflow = (
            IncidentWorkflow.objects.all()
            .filter(
                incident=self,
            )
            .values_list("workflow")
        )
        regulation = (
            SectorRegulationWorkflow.objects.all()
            .filter(
                sector_regulation=self.sector_regulation,
            )
            .exclude(workflow__in=current_workflow)
            .order_by("position")
        )
        if len(regulation) > 0:
            return regulation[0].workflow
        else:
            return None

    def are_impacts_present(self):
        impacts = Impact.objects.all().filter(
            regulation=self.sector_regulation.regulation,
            sectors__in=self.affected_sectors.all(),
        )
        return impacts.count() > 0

    def get_all_workflows(self):
        workflows = self.sector_regulation.workflows.all().order_by(
            "sectorregulationworkflow__position"
        )
        return list(workflows)

    def get_workflows_completed(self):
        workflows = (
            self.incidentworkflow_set.all()
            .order_by("workflow__sectorregulationworkflow__position", "-timestamp")
            .distinct()
        )
        return workflows

    # TO DO : check if it returns always the correct values
    def get_latest_incident_workflows(self):
        incident_workflows = (
            IncidentWorkflow.objects.filter(
                incident=self,
            )
            .order_by("workflow", "-timestamp")
            .distinct("workflow")
        )

        return incident_workflows

    def get_latest_incident_workflow(self):
        incident_workflow = (
            IncidentWorkflow.objects.filter(
                incident=self,
            )
            .order_by("-timestamp")
            .first()
        )

        return incident_workflow

    def get_latest_incident_workflow_by_workflow(self, workflow):
        incident_workflow = (
            IncidentWorkflow.objects.filter(
                incident=self,
                workflow=workflow,
            )
            .order_by("-timestamp")
            .first()
        )

        return incident_workflow

    def get_previous_workflow(self, workflow):
        current = (
            SectorRegulationWorkflow.objects.all()
            .filter(
                sector_regulation=self.sector_regulation,
                workflow=workflow,
            )
            .first()
        )

        previous = (
            SectorRegulationWorkflow.objects.all()
            .filter(
                sector_regulation=self.sector_regulation,
                position__lt=current.position,
            )
            .order_by("-position")
            .first()
        )

        if previous is not None:
            return previous
        return False

    # check if the previous workflow is filled and no next workflow filled
    def is_fillable(self, workflow):
        if self.incident_status != "CLOSE":
            current = (
                SectorRegulationWorkflow.objects.all()
                .filter(
                    sector_regulation=self.sector_regulation,
                    workflow=workflow,
                )
                .first()
            )
            previous = (
                SectorRegulationWorkflow.objects.all()
                .filter(
                    sector_regulation=self.sector_regulation,
                    position__lt=current.position,
                )
                .order_by("-position")
                .first()
            )
            # i am first
            if previous is None:
                # check if there are other record than me
                existing_workflow = (
                    IncidentWorkflow.objects.all()
                    .filter(
                        incident=self,
                    )
                    .exclude(workflow=workflow)
                    .first()
                )
                if existing_workflow is None:
                    return True
            # i am not first
            else:
                previous_incident_workflow = (
                    IncidentWorkflow.objects.all()
                    .filter(
                        incident=self,
                        workflow=previous.workflow,
                    )
                    .first()
                )
                if previous_incident_workflow is not None:
                    next_workflows = (
                        SectorRegulationWorkflow.objects.all()
                        .filter(
                            sector_regulation=self.sector_regulation,
                            position__gt=current.position,
                        )
                        .order_by("-position")
                        .values_list("workflow", flat=True)
                    )
                    next_incident_workflows = (
                        IncidentWorkflow.objects.all()
                        .filter(
                            incident=self,
                            workflow__in=next_workflows,
                        )
                        .first()
                    )
                    # There are previous and no next sor we are good
                    if next_incident_workflows is None:
                        return True
            return False
        return False


# link between incident and workflow
class IncidentWorkflow(models.Model):
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE)
    workflow = models.ForeignKey(Workflow, on_delete=models.SET_NULL, null=True)
    # for versionning
    timestamp = models.DateTimeField(default=timezone.now)
    review_status = models.CharField(
        max_length=5,
        choices=REVIEW_STATUS,
        blank=False,
        default=WORKFLOW_REVIEW_STATUS[0][0],
    )
    impacts = models.ManyToManyField(
        Impact,
        default=None,
    )
    comment = models.TextField(null=True, blank=True)

    def get_previous_workflow(self):
        current = (
            SectorRegulationWorkflow.objects.all()
            .filter(
                sector_regulation=self.incident.sector_regulation,
                workflow=self.workflow,
            )
            .first()
        )

        previous = (
            SectorRegulationWorkflow.objects.all()
            .filter(
                sector_regulation=self.incident.sector_regulation,
                position__lt=current.position,
            )
            .order_by("-position")
            .first()
        )

        if previous is not None:
            return previous
        return False

    def get_next_workflow(self):
        current = (
            SectorRegulationWorkflow.objects.all()
            .filter(
                sector_regulation=self.incident.sector_regulation,
                workflow=self.workflow,
            )
            .first()
        )

        next = (
            SectorRegulationWorkflow.objects.all()
            .filter(
                sector_regulation=self.incident.sector_regulation,
                position__gt=current.position,
            )
            .order_by("position")
            .first()
        )

        if next is not None:
            return next.workflow
        return False


# answers
class Answer(models.Model):
    incident_workflow = models.ForeignKey(IncidentWorkflow, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    answer = models.TextField(null=True, blank=True)
    predefined_answers = models.ManyToManyField(PredefinedAnswer, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)

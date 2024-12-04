# Generated by Django 5.1.2 on 2024-12-04 14:43

import uuid

import django.db.models.deletion
import django.utils.timezone
import parler.fields
import parler.models
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        (
            "governanceplatform",
            "0036_alter_functionality_type_delete_sectorcompanycontact",
        ),
    ]

    operations = [
        migrations.CreateModel(
            name="AssetData",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4, unique=True, verbose_name="uuid"
                    ),
                ),
            ],
            options={
                "verbose_name": "Assets",
                "verbose_name_plural": "Asset",
            },
            bases=(parler.models.TranslatableModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name="RecommendationData",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "code",
                    models.CharField(
                        max_length=255, verbose_name="Recommendation name"
                    ),
                ),
                (
                    "description",
                    models.TextField(verbose_name="Recommendation description"),
                ),
                (
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4, unique=True, verbose_name="uuid"
                    ),
                ),
                (
                    "status",
                    models.BooleanField(
                        default=False, verbose_name="Status of the recommendation"
                    ),
                ),
                ("due_date", models.DateTimeField(null=True, verbose_name="Due date")),
            ],
            options={
                "verbose_name": "Recommendation",
                "verbose_name_plural": "Recommendations",
            },
        ),
        migrations.CreateModel(
            name="ThreatData",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4, unique=True, verbose_name="uuid"
                    ),
                ),
            ],
            options={
                "verbose_name": "Threat",
                "verbose_name_plural": "Threats",
            },
            bases=(parler.models.TranslatableModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name="VulnerabilityData",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4, unique=True, verbose_name="uuid"
                    ),
                ),
            ],
            options={
                "verbose_name": "Vulnerability",
                "verbose_name_plural": "Vulnerabilities",
            },
            bases=(parler.models.TranslatableModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name="CompanyReporting",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("year", models.PositiveIntegerField()),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="governanceplatform.company",
                        verbose_name="Company",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ObservationRecommendation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "code",
                    models.CharField(
                        max_length=255, verbose_name="Recommendation name"
                    ),
                ),
                (
                    "is_generic",
                    models.BooleanField(default=False, verbose_name="Is Generic ?"),
                ),
                (
                    "creation_date",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="Creation date"
                    ),
                ),
                (
                    "sectors",
                    models.ManyToManyField(
                        to="governanceplatform.company", verbose_name="Sectors"
                    ),
                ),
            ],
            options={
                "verbose_name": "Recommendation for observation",
                "verbose_name_plural": "Recommendations for observation",
            },
            bases=(parler.models.TranslatableModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name="Observation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "company_reporting",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="reporting.companyreporting",
                        verbose_name="Risk Analysis",
                    ),
                ),
                (
                    "observation_recommendations",
                    models.ManyToManyField(
                        to="reporting.observationrecommendation",
                        verbose_name="Observation recommendations",
                    ),
                ),
            ],
            options={
                "verbose_name": "Observation",
                "verbose_name_plural": "Observations",
            },
        ),
        migrations.CreateModel(
            name="SectorReportConfiguration",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "reporting_year",
                    models.PositiveIntegerField(verbose_name="Reporting year"),
                ),
                (
                    "number_of_year",
                    models.PositiveSmallIntegerField(
                        verbose_name="Number of year to compare"
                    ),
                ),
                (
                    "threshold_for_high_risk",
                    models.FloatField(verbose_name="High risk rate threshold"),
                ),
                (
                    "top_ranking",
                    models.PositiveSmallIntegerField(
                        choices=[(3, "Top 3"), (5, "Top 5"), (10, "Top 10")],
                        verbose_name="Ranking",
                    ),
                ),
                (
                    "sector",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="governanceplatform.sector",
                        verbose_name="Sector",
                    ),
                ),
            ],
            options={
                "verbose_name": "Configuration",
                "verbose_name_plural": "Configurations",
            },
        ),
        migrations.CreateModel(
            name="SectorStatistic",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "timestamp",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="Timestamp"
                    ),
                ),
                (
                    "high_risk_average",
                    models.FloatField(verbose_name="Average high risk"),
                ),
                ("risk_average", models.FloatField(verbose_name="High risk")),
                (
                    "sector",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="governanceplatform.sector",
                        verbose_name="Sector",
                    ),
                ),
            ],
            options={
                "verbose_name": "Sector stat",
                "verbose_name_plural": "Sector stats",
            },
        ),
        migrations.CreateModel(
            name="ServiceStat",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "total_risks",
                    models.FloatField(default=0, verbose_name="Total of all risks"),
                ),
                (
                    "total_untreated_risks",
                    models.FloatField(
                        default=0, verbose_name="Total of untreated risks"
                    ),
                ),
                (
                    "total_treated_risks",
                    models.FloatField(default=0, verbose_name="Total of treated risks"),
                ),
                (
                    "total_reduced_risks",
                    models.FloatField(default=0, verbose_name="Total of reduced risks"),
                ),
                (
                    "total_denied_risks",
                    models.FloatField(default=0, verbose_name="Total of denied risks"),
                ),
                (
                    "total_accepted_risks",
                    models.FloatField(
                        default=0, verbose_name="Total of accepted risks"
                    ),
                ),
                (
                    "total_shared_risks",
                    models.FloatField(default=0, verbose_name="Total of shared risks"),
                ),
                (
                    "total_high_risks_treated",
                    models.FloatField(
                        default=0, verbose_name="Total high risks treated"
                    ),
                ),
                (
                    "avg_high_risk_treated",
                    models.FloatField(
                        default=0, verbose_name="Average high risks treated"
                    ),
                ),
                (
                    "avg_current_risks",
                    models.FloatField(
                        default=0, verbose_name="Average of current risks"
                    ),
                ),
                (
                    "avg_residual_risks",
                    models.FloatField(
                        default=0, verbose_name="Average of residual risks"
                    ),
                ),
                (
                    "company_reporting",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="reporting.companyreporting",
                        verbose_name="Risk Analysis",
                    ),
                ),
                (
                    "service",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="reporting.assetdata",
                        verbose_name="Asset",
                    ),
                ),
            ],
            options={
                "verbose_name": "Risk analysis stat",
                "verbose_name_plural": "Risk analysis stats",
            },
        ),
        migrations.CreateModel(
            name="RiskData",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("uuid", models.UUIDField(default=uuid.uuid4, verbose_name="uuid")),
                ("threat_value", models.FloatField(verbose_name="Threat value")),
                (
                    "vulnerability_value",
                    models.FloatField(verbose_name="Vulnerability value"),
                ),
                (
                    "residual_risk_level_value",
                    models.FloatField(
                        default=-1, verbose_name="Residual risk level value"
                    ),
                ),
                (
                    "risk_treatment",
                    models.CharField(
                        choices=[
                            ("REDUC", "Reduction"),
                            ("DENIE", "Deny"),
                            ("ACCEP", "Acceptation"),
                            ("SHARE", "Shared"),
                            ("UNTRE", "Untreated"),
                        ],
                        default="DENIE",
                        max_length=5,
                        verbose_name="Risk treatment",
                    ),
                ),
                (
                    "max_risk",
                    models.FloatField(default=-1, verbose_name="Maximum risk"),
                ),
                (
                    "risk_c",
                    models.FloatField(default=-1, verbose_name="Confidentility risk"),
                ),
                (
                    "risk_i",
                    models.FloatField(default=-1, verbose_name="Integrity risk"),
                ),
                (
                    "risk_a",
                    models.FloatField(default=-1, verbose_name="Availability risk"),
                ),
                (
                    "impact_c",
                    models.FloatField(default=-1, verbose_name="Confidentility impact"),
                ),
                (
                    "impact_i",
                    models.FloatField(default=-1, verbose_name="Integrity impact"),
                ),
                (
                    "impact_a",
                    models.FloatField(default=-1, verbose_name="Availability impact"),
                ),
                (
                    "asset",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="reporting.assetdata",
                        verbose_name="Asset",
                    ),
                ),
                (
                    "recommendations",
                    models.ManyToManyField(
                        to="reporting.recommendationdata",
                        verbose_name="recommendations",
                    ),
                ),
                (
                    "service",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="reporting.servicestat",
                        verbose_name="Service",
                    ),
                ),
                (
                    "threat",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="reporting.threatdata",
                        verbose_name="Threat",
                    ),
                ),
                (
                    "vulnerability",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="reporting.vulnerabilitydata",
                        verbose_name="Vulnerability",
                    ),
                ),
            ],
            options={
                "verbose_name": "Risk",
                "verbose_name_plural": "Risks",
            },
        ),
        migrations.CreateModel(
            name="AssetDataTranslation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "language_code",
                    models.CharField(
                        db_index=True, max_length=15, verbose_name="Language"
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        blank=True,
                        default=None,
                        max_length=255,
                        null=True,
                        verbose_name="Name",
                    ),
                ),
                (
                    "master",
                    parler.fields.TranslationsForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="translations",
                        to="reporting.assetdata",
                    ),
                ),
            ],
            options={
                "verbose_name": "Assets Translation",
                "db_table": "reporting_assetdata_translation",
                "db_tablespace": "",
                "managed": True,
                "default_permissions": (),
                "unique_together": {("language_code", "master")},
            },
            bases=(parler.models.TranslatedFieldsModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name="ObservationRecommendationTranslation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "language_code",
                    models.CharField(
                        db_index=True, max_length=15, verbose_name="Language"
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True, default=None, null=True, verbose_name="description"
                    ),
                ),
                (
                    "master",
                    parler.fields.TranslationsForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="translations",
                        to="reporting.observationrecommendation",
                    ),
                ),
            ],
            options={
                "verbose_name": "Recommendation for observation Translation",
                "db_table": "reporting_observationrecommendation_translation",
                "db_tablespace": "",
                "managed": True,
                "default_permissions": (),
                "unique_together": {("language_code", "master")},
            },
            bases=(parler.models.TranslatedFieldsModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name="ThreatDataTranslation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "language_code",
                    models.CharField(
                        db_index=True, max_length=15, verbose_name="Language"
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        blank=True,
                        default=None,
                        max_length=255,
                        null=True,
                        verbose_name="Name",
                    ),
                ),
                (
                    "master",
                    parler.fields.TranslationsForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="translations",
                        to="reporting.threatdata",
                    ),
                ),
            ],
            options={
                "verbose_name": "Threat Translation",
                "db_table": "reporting_threatdata_translation",
                "db_tablespace": "",
                "managed": True,
                "default_permissions": (),
                "unique_together": {("language_code", "master")},
            },
            bases=(parler.models.TranslatedFieldsModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name="VulnerabilityDataTranslation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "language_code",
                    models.CharField(
                        db_index=True, max_length=15, verbose_name="Language"
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        blank=True,
                        default=None,
                        max_length=255,
                        null=True,
                        verbose_name="Name",
                    ),
                ),
                (
                    "master",
                    parler.fields.TranslationsForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="translations",
                        to="reporting.vulnerabilitydata",
                    ),
                ),
            ],
            options={
                "verbose_name": "Vulnerability Translation",
                "db_table": "reporting_vulnerabilitydata_translation",
                "db_tablespace": "",
                "managed": True,
                "default_permissions": (),
                "unique_together": {("language_code", "master")},
            },
            bases=(parler.models.TranslatedFieldsModelMixin, models.Model),
        ),
    ]

# Generated by Django 5.1.1 on 2024-09-24 11:46

import django.db.models.deletion
import parler.fields
import parler.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("governanceplatform", "0024_alter_regulationtranslation_label"),
    ]

    operations = [
        migrations.CreateModel(
            name="EntityCategory",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("code", models.CharField(max_length=255, verbose_name="Code")),
                (
                    "regulation",
                    models.ForeignKey(
                        blank=True,
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="governanceplatform.regulation",
                        verbose_name="Regulation",
                    ),
                ),
            ],
            options={
                "verbose_name": "Entity category",
                "verbose_name_plural": "Entity categories",
            },
            bases=(parler.models.TranslatableModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name="EntityCategoryTranslation",
            fields=[
                (
                    "id",
                    models.AutoField(
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
                ("label", models.CharField(max_length=255, verbose_name="Label")),
                (
                    "master",
                    parler.fields.TranslationsForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="translations",
                        to="governanceplatform.entitycategory",
                    ),
                ),
            ],
            options={
                "verbose_name": "Entity category Translation",
                "db_table": "governanceplatform_entitycategory_translation",
                "db_tablespace": "",
                "managed": True,
                "default_permissions": (),
                "unique_together": {("language_code", "master")},
            },
            bases=(parler.models.TranslatedFieldsModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name="ObserverRegulation",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "is_spoc",
                    models.BooleanField(
                        default=False, verbose_name="is single point of contact"
                    ),
                ),
                (
                    "incident_rule",
                    models.JSONField(
                        blank=True,
                        default=None,
                        null=True,
                        verbose_name="Incident rules",
                    ),
                ),
                (
                    "observer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="governanceplatform.observer",
                        verbose_name="Observer",
                    ),
                ),
                (
                    "regulation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="governanceplatform.regulation",
                        verbose_name="Regulation",
                    ),
                ),
            ],
            options={
                "verbose_name": "Observer regulation",
                "verbose_name_plural": "Observer regulations",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("regulation", "observer"),
                        name="unique_Observerregulation",
                    )
                ],
            },
        ),
    ]

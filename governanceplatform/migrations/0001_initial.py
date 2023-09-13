# Generated by Django 4.2.1 on 2023-09-13 13:09

import django.db.models.deletion
import django.utils.timezone
import parler.fields
import parler.models
from django.conf import settings
from django.db import migrations, models

import governanceplatform.helpers


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="User",
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
                ("password", models.CharField(max_length=128, verbose_name="password")),
                (
                    "last_login",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="last login"
                    ),
                ),
                (
                    "is_superuser",
                    models.BooleanField(
                        default=False,
                        help_text="Designates that this user has all permissions without explicitly assigning them.",
                        verbose_name="superuser status",
                    ),
                ),
                (
                    "first_name",
                    models.CharField(
                        blank=True, max_length=150, verbose_name="first name"
                    ),
                ),
                (
                    "last_name",
                    models.CharField(
                        blank=True, max_length=150, verbose_name="last name"
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Designates whether this user should be treated as active. Unselect this instead of deleting accounts.",
                        verbose_name="active",
                    ),
                ),
                (
                    "date_joined",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="date joined"
                    ),
                ),
                (
                    "email",
                    models.EmailField(
                        error_messages={
                            "unique": "A user is already registered with this email address"
                        },
                        max_length=254,
                        unique=True,
                        verbose_name="email address",
                    ),
                ),
                (
                    "phone_number",
                    models.CharField(
                        blank=True, default=None, max_length=30, null=True
                    ),
                ),
                (
                    "proxy_token",
                    models.CharField(
                        default=governanceplatform.helpers.generate_token,
                        max_length=255,
                        unique=True,
                    ),
                ),
                (
                    "is_staff",
                    models.BooleanField(
                        default=False,
                        help_text="Designates whether the user can log into this admin site.",
                        verbose_name="Administrator",
                    ),
                ),
            ],
            options={
                "permissions": (
                    ("import_user", "Can import user"),
                    ("export_user", "Can export user"),
                ),
            },
        ),
        migrations.CreateModel(
            name="Company",
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
                    "is_regulator",
                    models.BooleanField(default=False, verbose_name="Regulator"),
                ),
                (
                    "identifier",
                    models.CharField(max_length=64, verbose_name="Identifier"),
                ),
                ("name", models.CharField(max_length=64, verbose_name="name")),
                ("country", models.CharField(max_length=64, verbose_name="country")),
                ("address", models.CharField(max_length=255, verbose_name="address")),
                (
                    "email",
                    models.CharField(
                        blank=True,
                        default=None,
                        max_length=100,
                        null=True,
                        verbose_name="email address",
                    ),
                ),
                (
                    "phone_number",
                    models.CharField(
                        blank=True,
                        default=None,
                        max_length=30,
                        null=True,
                        verbose_name="phone number",
                    ),
                ),
                (
                    "monarc_path",
                    models.CharField(max_length=200, verbose_name="MONARC URL"),
                ),
            ],
            options={
                "verbose_name": "Company",
                "verbose_name_plural": "Companies",
            },
        ),
        migrations.CreateModel(
            name="Functionality",
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
            ],
            options={
                "verbose_name": "Functionality",
                "verbose_name_plural": "Functionalities",
            },
            bases=(parler.models.TranslatableModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name="OperatorType",
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
                    "functionalities",
                    models.ManyToManyField(to="governanceplatform.functionality"),
                ),
            ],
            options={
                "abstract": False,
            },
            bases=(parler.models.TranslatableModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name="Sector",
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
                    "parent",
                    models.ForeignKey(
                        blank=True,
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="governanceplatform.sector",
                        verbose_name="parent",
                    ),
                ),
            ],
            options={
                "verbose_name": "Sector",
                "verbose_name_plural": "Sectors",
            },
            bases=(parler.models.TranslatableModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name="Services",
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
                    "sector",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="governanceplatform.sector",
                    ),
                ),
            ],
            options={
                "verbose_name": "Service",
                "verbose_name_plural": "Services",
            },
            bases=(parler.models.TranslatableModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name="SectorContact",
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
                    "is_sector_contact",
                    models.BooleanField(default=False, verbose_name="Contact person"),
                ),
                (
                    "sector",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="governanceplatform.sector",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Sector contact",
                "verbose_name_plural": "Sectors contact",
            },
        ),
        migrations.CreateModel(
            name="OperatorTypeTranslation",
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
                ("type", models.CharField(max_length=100)),
                (
                    "master",
                    parler.fields.TranslationsForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="translations",
                        to="governanceplatform.operatortype",
                    ),
                ),
            ],
            options={
                "verbose_name": "operator type Translation",
                "db_table": "governanceplatform_operatortype_translation",
                "db_tablespace": "",
                "managed": True,
                "default_permissions": (),
            },
            bases=(parler.models.TranslatedFieldsModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name="FunctionalityTranslation",
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
                ("name", models.CharField(max_length=100)),
                (
                    "master",
                    parler.fields.TranslationsForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="translations",
                        to="governanceplatform.functionality",
                    ),
                ),
            ],
            options={
                "verbose_name": "Functionality Translation",
                "db_table": "governanceplatform_functionality_translation",
                "db_tablespace": "",
                "managed": True,
                "default_permissions": (),
            },
            bases=(parler.models.TranslatedFieldsModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name="CompanyAdministrator",
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
                    "is_company_administrator",
                    models.BooleanField(default=False, verbose_name="Administrator"),
                ),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="governanceplatform.company",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Company administrator",
                "verbose_name_plural": "Company administrator",
            },
        ),
        migrations.AddField(
            model_name="company",
            name="sectors",
            field=models.ManyToManyField(to="governanceplatform.sector"),
        ),
        migrations.AddField(
            model_name="company",
            name="types",
            field=models.ManyToManyField(to="governanceplatform.operatortype"),
        ),
        migrations.AddField(
            model_name="user",
            name="companies",
            field=models.ManyToManyField(
                through="governanceplatform.CompanyAdministrator",
                to="governanceplatform.company",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="groups",
            field=models.ManyToManyField(
                blank=True,
                help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
                related_name="user_set",
                related_query_name="user",
                to="auth.group",
                verbose_name="groups",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="sectors",
            field=models.ManyToManyField(
                through="governanceplatform.SectorContact",
                to="governanceplatform.sector",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="user_permissions",
            field=models.ManyToManyField(
                blank=True,
                help_text="Specific permissions for this user.",
                related_name="user_set",
                related_query_name="user",
                to="auth.permission",
                verbose_name="user permissions",
            ),
        ),
        migrations.CreateModel(
            name="ServicesTranslation",
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
                ("name", models.CharField(max_length=100)),
                (
                    "master",
                    parler.fields.TranslationsForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="translations",
                        to="governanceplatform.services",
                    ),
                ),
            ],
            options={
                "verbose_name": "Service Translation",
                "db_table": "governanceplatform_services_translation",
                "db_tablespace": "",
                "managed": True,
                "default_permissions": (),
                "unique_together": {("language_code", "master")},
            },
            bases=(parler.models.TranslatedFieldsModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name="SectorTranslation",
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
                ("name", models.CharField(max_length=100)),
                (
                    "master",
                    parler.fields.TranslationsForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="translations",
                        to="governanceplatform.sector",
                    ),
                ),
            ],
            options={
                "verbose_name": "Sector Translation",
                "db_table": "governanceplatform_sector_translation",
                "db_tablespace": "",
                "managed": True,
                "default_permissions": (),
                "unique_together": {("language_code", "master")},
            },
            bases=(parler.models.TranslatedFieldsModelMixin, models.Model),
        ),
        migrations.AddConstraint(
            model_name="sectorcontact",
            constraint=models.UniqueConstraint(
                fields=("user", "sector"), name="unique_SectorContact"
            ),
        ),
        migrations.AlterUniqueTogether(
            name="operatortypetranslation",
            unique_together={("language_code", "master")},
        ),
        migrations.AlterUniqueTogether(
            name="functionalitytranslation",
            unique_together={("language_code", "master")},
        ),
        migrations.AddConstraint(
            model_name="companyadministrator",
            constraint=models.UniqueConstraint(
                fields=("user", "company"), name="unique_CompanyAdministrator"
            ),
        ),
    ]

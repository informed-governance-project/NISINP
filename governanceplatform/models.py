from django.contrib import admin
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from parler.models import TranslatableModel, TranslatedFields


# sector
class Sector(TranslatableModel):
    translations = TranslatedFields(name=models.CharField(max_length=100))
    parent = models.ForeignKey(
        "self",
        null=True,
        on_delete=models.CASCADE,
        blank=True,
        default=None,
        verbose_name=_("parent"),
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Sector")
        verbose_name_plural = _("Sectors")


# esssential services
class Services(TranslatableModel):
    translations = TranslatedFields(name=models.CharField(max_length=100))
    sector = models.ForeignKey(Sector, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Service")
        verbose_name_plural = _("Services")

# functionality (e.g, risk analysis, SO)
class Functionality(TranslatableModel):
    translations = TranslatedFields(name=models.CharField(max_length=100))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Functionality")
        verbose_name_plural = _("Functionalities")


# operator has type (critical, essential, etc.) who give access to functionalities 
class OperatorType(TranslatableModel):
    translations = TranslatedFields(type=models.CharField(max_length=100))
    functionalities = models.ManyToManyField(Functionality)

    def __str__(self):
        return self.type


# regulator and operator are companies
class Company(models.Model):
    is_regulator = models.BooleanField(default=False, verbose_name=_("Regulator"))
    identifier = models.CharField(
        max_length=64, verbose_name=_("Identifier")
    )  # requirement from business concat(name_country_regulator)
    name = models.CharField(max_length=64, verbose_name=_("name"))
    country = models.CharField(max_length=64, verbose_name=_("country"))
    address = models.CharField(max_length=255, verbose_name=_("address"))
    email = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default=None,
        verbose_name=_("email address"),
    )
    phone_number = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        default=None,
        verbose_name=_("phone number"),
    )
    sectors = models.ManyToManyField(Sector)
    monarc_path = models.CharField(max_length=200, verbose_name="MONARC URL")

    def __str__(self):
        return self.name

    @admin.display(description="sectors")
    def get_sectors(self):
        return [sector.name for sector in self.sectors.all()]

    class Meta:
        verbose_name = _("Company")
        verbose_name_plural = _("Companies")


# define a token class for SSO on other application/module
class ExternalToken(models.Model):
    token = models.CharField(max_length=255)
    module_path = models.CharField(max_length=255)
    module_name = models.CharField(max_length=255)


# define an abstract class which make  the difference between operator and regulator
class User(AbstractUser):
    username = None
    is_regulator = models.BooleanField(default=False, verbose_name=_("Regulator"))
    is_staff = models.BooleanField(
        verbose_name=_("Administrator"),
        default=False,
        help_text=_("Designates whether the user can log into this admin site."),
    )
    phone_number = models.CharField(max_length=30, blank=True, default=None)
    companies = models.ManyToManyField(Company)
    sectors = models.ManyToManyField(Sector, through="SectorAdministration")
    email = models.EmailField(
        verbose_name=_("email address"),
        unique=True,
        error_messages={
            "unique": _("A user is already registered with this email address"),
        },
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    @admin.display(description="sectors")
    def get_sectors(self):
        return [sector.name for sector in self.sectors.all()]

    @admin.display(description="companies")
    def get_companies(self):
        return [company.name for company in self.companies.all()]


# link between the users and the sector
class SectorAdministration(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    sector = models.ForeignKey(Sector, on_delete=models.CASCADE)
    is_sector_administrator = models.BooleanField(
        default=False, verbose_name=_("Administrator")
    )

    class Meta:
        verbose_name = _("Sector administration")
        verbose_name_plural = _("Sectors administration")

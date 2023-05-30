from django.contrib import admin
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from parler.models import TranslatableModel, TranslatedFields


# sector
class Sector(TranslatableModel):
    translations = TranslatedFields(name=models.CharField(max_length=100))
    parent = models.ForeignKey("self", null=True, on_delete=models.CASCADE)

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


# regulator and operator are companies
class Company(models.Model):
    is_regulator = models.BooleanField(default=False)
    identifier = models.CharField(
        max_length=64
    )  # requirement from business concat(name_country_regulator)
    name = models.CharField(max_length=64)
    country = models.CharField(max_length=64)
    address = models.CharField(max_length=255)
    email = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=30, blank=True, null=True)
    sectors = models.ManyToManyField(Sector)
    monarc_path = models.CharField(max_length=200)

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
    is_regulator = models.BooleanField(default=False)
    is_administrator = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=30)
    companies = models.ManyToManyField(Company)
    sectors = models.ManyToManyField(Sector, through='SectorAdministration')

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
    is_sector_administrator = models.BooleanField(default=False)

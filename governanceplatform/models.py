from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


# sector
class Sector(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey("self", null=True, on_delete=models.CASCADE)

    class Meta:
        verbose_name = _("Sector")
        verbose_name_plural = _("Sectors")


# regulator and operator are companies
class Company(models.Model):
    is_operateur = models.BooleanField(default=True)
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
    is_operateur = models.BooleanField(default=True)
    is_regulator = models.BooleanField(default=False)
    is_administrator = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=30)
    companies = models.ManyToManyField(Company)
    sectors = models.ManyToManyField(Sector)

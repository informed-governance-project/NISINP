from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

#regulator and operator are companies
class Company(models.Model):
    is_operateur = models.BooleanField(default=True)
    is_regulator = models.BooleanField(default=False)
    identifier = models.CharField(max_length=64) #requirement from business concat(name_country_regulator)
    name = models.CharField(max_length=64)
    country = models.CharField(max_length=64) 
    adress = models.CharField(max_length=255)
    email = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=30, blank=True, null=True)

    monarc_path = models.CharField(max_length=200)

#define an abstract class which make  the difference between operator and regulator
class User(AbstractUser):
    is_operateur = models.BooleanField(default=True)
    is_regulator = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=30)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)

#sector 
class Sector(models.Model):
    name = models.CharField(max_length=100)
    parent_id = models.ForeignKey('self', null=True, on_delete=models.CASCADE)


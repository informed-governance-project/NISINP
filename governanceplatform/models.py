from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

#define an abstract class to make easily the difference between operator and regulator
class User(AbstractUser):
    email = models.EmailField(unique=True)
    is_operateur = models.BooleanField(default=True)
    is_regulator = models.BooleanField(default=False)
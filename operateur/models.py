# from django.db import models

# Create your models here.

from __future__ import annotations

import uuid
from typing import Any

from django.db import models
from django.db.models import Sum
from governanceplatform.models import User

class RightMixin:
    @staticmethod
    def _fields_base_write():
        return set()

    @staticmethod
    def _fields_base_read():
        return {"id"}

    @classmethod
    def fields_base_write(cls):
        return cls._fields_base_write()

    @classmethod
    def fields_base_read(cls):
        return cls._fields_base_write().union(cls._fields_base_read())

    def dump(self):
        dict = {k: getattr(self, k) for k in self.fields_base_read()}
        # if hasattr(self, "__dump__"):
        #     dict = self.__dump__()
        for key, value in dict.items():
            if isinstance(value, models.Model):
                if hasattr(value, "dump"):
                    dict[key] = value.dump()
                else:
                    dict[key] = str(value)
            elif value.__class__.__name__ == "ManyRelatedManager":
                if hasattr(value, "__dump__"):
                    dict[key] = [elem.__dump__() for elem in value.all()]
                else:
                    dict[key] = [str(elem) for elem in value.all()]
        return dict

class Operateur(models.Model):
    operateur_id = models.UUIDField(default=uuid.uuid4, unique=True) #use for DB purpose
    operateur_identifier = models.CharField(max_length=64) #requirement from business concat(name_country_regulator)
    operateur_name = models.CharField(max_length=64)
    operateur_country = models.CharField(max_length=64) 
    operateur_adress = models.CharField(max_length=255)
    operateur_email = models.CharField(max_length=100, blank=True, null=True)
    operateur_phone_number = models.CharField(max_length=30, blank=True, null=True)

    operateur_monarc_path = models.CharField(max_length=200)

class OperateurUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    entity_id = models.ForeignKey(Operateur, on_delete=models.CASCADE)
    user_phone_number = models.CharField(max_length=30)
        
    class Meta:
        db_table = 'users'
        managed = True


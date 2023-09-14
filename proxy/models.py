from django.db import models
from portal.helpers import generate_token


class Module(models.Model):
    """Proxified module of the platform."""

    name = models.CharField(max_length=255, unique=True)
    path = models.CharField(max_length=255, unique=True)
    upstream = models.CharField(max_length=255, unique=True)
    authentication_required = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ExternalToken(models.Model):
    """Token class."""

    token = models.CharField(
        max_length=255, unique=True, null=False, default=generate_token
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    user = models.ForeignKey("governanceproject.User", on_delete=models.CASCADE)
    module = models.ForeignKey(Module, on_delete=models.CASCADE)

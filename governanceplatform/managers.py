from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext as _

from .permissions import set_platform_admin_permissions


class CustomUserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifier
    for authentication instead of usernames.
    """

    def create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError(_("User must have an email address"))
        email = self.normalize_email(email)
        if 'email' in extra_fields:
            del extra_fields['email']
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))

        # Create the superuser
        extra_fields.pop("email", None)
        user = self.create_user(email=email, password=password, **extra_fields)
        # Platform Admin permissions
        set_platform_admin_permissions(user)

        return user

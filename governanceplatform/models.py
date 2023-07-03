from django.contrib import admin
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from parler.models import TranslatableModel, TranslatedFields

from .managers import CustomUserManager


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
    types = models.ManyToManyField(OperatorType)
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
    is_staff = models.BooleanField(
        verbose_name=_("Administrator"),
        default=False,
        help_text=_("Designates whether the user can log into this admin site."),
    )
    phone_number = models.CharField(max_length=30, blank=True, default=None, null=True)
    companies = models.ManyToManyField(Company, through="CompanyAdministrator")
    sectors = models.ManyToManyField(Sector, through="SectorContact")
    email = models.EmailField(
        verbose_name=_("email address"),
        unique=True,
        error_messages={
            "unique": _("A user is already registered with this email address"),
        },
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = CustomUserManager()

    @admin.display(description="sectors")
    def get_sectors(self):
        return [sector.name for sector in self.sectors.all()]

    @admin.display(description="companies")
    def get_companies(self):
        return [company.name for company in self.companies.all()]


# link between the users and the sector
class SectorContact(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    sector = models.ForeignKey(Sector, on_delete=models.CASCADE)
    is_sector_contact = models.BooleanField(
        default=False, verbose_name=_("Contact person")
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "sector"], name="unique_SectorContact"
            ),
        ]
        verbose_name = _("Sector contact")
        verbose_name_plural = _("Sectors contact")


# link between the admin users and the companies
class CompanyAdministrator(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    is_company_administrator = models.BooleanField(
        default=False, verbose_name=_("Administrator")
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "company"], name="unique_CompanyAdministrator"
            ),
        ]
        verbose_name = _("Company administrator")
        verbose_name_plural = _("Company administrator")


@receiver(post_save, sender=CompanyAdministrator)
def create_user_groups(sender, instance, created, **kwargs):
    user = instance.user
    user.is_staff = False
    user.is_superuser = False

    group_permissions = {}
    some_company_is_regulator = user.companyadministrator_set.filter(
        company__is_regulator=True
    )
    some_company_is_administrator = user.companyadministrator_set.filter(
        is_company_administrator=True
    )

    # Define a dictionary of group names and the associated permissions

    if (
        some_company_is_administrator.exists()
        and some_company_is_administrator.filter(company__is_regulator=False).exists()
    ):
        user.is_staff = True
        group_permissions["OperatorAdmin"] = [
            "governanceplatform.add_user",
            "governanceplatform.change_user",
            "governanceplatform.delete_user",
        ]

    if (
        some_company_is_regulator.exists()
        and some_company_is_regulator.filter(is_company_administrator=True).exists()
    ):
        # Regulator Administrator permissions
        user.is_staff = True
        user.is_superuser = True

    if (
        some_company_is_regulator.exists()
        and some_company_is_regulator.filter(is_company_administrator=False).exists()
    ):
        # Regulator Staff permission
        user.is_staff = True
        group_permissions["RegulatorStaff"] = [
            "governanceplatform.add_user",
            "governanceplatform.change_user",
            "governanceplatform.delete_user",
        ]

    if not group_permissions or user.groups.exists():
        user.groups.clear()

    # Create or retrieve the groups and assign permissions
    if group_permissions:
        for group_name, permissions in group_permissions.items():
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                for permission in permissions:
                    app_label, codename = permission.split(".", 1)
                    group.permissions.add(
                        Permission.objects.get(
                            content_type__app_label=app_label, codename=codename
                        )
                    )
            # Add the user to the group
            user.groups.add(group)

    user.save()


@receiver(post_delete, sender=CompanyAdministrator)
def post_delete_handler(sender, instance, **kwargs):
    user = instance.user
    group = Group.objects.get(name="OperatorAdmin")

    if not user.companyadministrator_set.all().exists():
        user.is_staff = False
        user.is_superuser = False

    if instance.company.is_regulator:
        group = Group.objects.get(name="RegulatorStaff")

    # Remove the group from the user
    if user.groups.filter(name=group.name).exists():
        user.groups.remove(group)

    user.save()

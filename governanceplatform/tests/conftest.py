import pytest
from django.contrib.auth.models import Group
from django.db import models
from django.test import Client
from django.utils import timezone
from django.utils.translation import activate
from parler.models import TranslatableModel

from governanceplatform.models import (
    Company,
    EntityCategory,
    Functionality,
    Observer,
    Regulation,
    Regulator,
    Sector,
    User,
)
from governanceplatform.permissions import update_all_group_permissions
from governanceplatform.tests.data import (
    companies_data,
    functionalities_data,
    observers_data,
    permission_groups,
    regulations,
    regulators_data,
    sectors,
    users,
)


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def populate_db(db):
    """
    Populate the DB
    """

    # Force default language for translatable
    activate("en")

    # Dependencies M2M
    entity_category = EntityCategory.objects.create(label="Critical")

    # Create companies
    created_companies = import_from_json(Company, companies_data)

    # Create functionnality
    created_functionalities = import_from_json(Functionality, functionalities_data)

    # Create regulators
    created_regulators = import_from_json(Regulator, regulators_data)

    # Create an observer
    created_observers = import_from_json(Observer, observers_data)

    # Create permission groups
    created_permission_groups = import_from_json(Group, permission_groups)

    # Create sectors
    created_sectors = import_from_json(Sector, sectors)

    # Create regulations
    created_regulations = import_from_json(Regulation, regulations)

    # Create users
    created_users = import_from_json(User, users)
    # special set for user and permissions
    initialize_user(created_users)
    link_entity_user(users, created_users)
    update_all_group_permissions()

    return {
        "companies": created_companies,
        "functionnalities": created_functionalities,
        "regulators": created_regulators,
        "observers": created_observers,
        "entity_categories": [entity_category],
        "permissions_groups": created_permission_groups,
        "sectors": created_sectors,
        "regulations": created_regulations,
        "users": created_users,
    }


def get_unique_lookup(model, data: dict):
    unique_fields = [
        f.name for f in model._meta.get_fields() if getattr(f, "unique", False)
    ]

    for constraint in model._meta.constraints:
        if isinstance(constraint, models.UniqueConstraint):
            unique_fields.extend(constraint.fields)

    simple_fields = [
        f.name
        for f in model._meta.get_fields()
        if not (f.many_to_many or f.one_to_many or f.is_relation)
    ]

    lookup = {f: data[f] for f in unique_fields if f in data and f in simple_fields}
    return lookup


def get_or_create_related(related_model, val: dict):
    if not isinstance(val, dict):
        raise ValueError(f"Unexpected value {related_model.__name__}: {val}")

    lookup = get_unique_lookup(related_model, val)
    object = None
    if not lookup:
        # bypass when there is no unique field in the model, only get, no create
        object = related_model.objects.filter(**lookup).first()
        if not object:
            raise ValueError(
                f"Unexpected lookup for {related_model.__name__} with data={val}"
            )

    if not object:
        obj, created = related_model.objects.get_or_create(**lookup)
    else:
        created = False
        obj = object

    if created:
        # update other field
        for k, v in val.items():
            if k not in lookup:
                setattr(obj, k, v)

        # update translations
        if isinstance(obj, TranslatableModel):
            obj.set_current_language("en")
            for f in obj._parler_meta.get_translated_fields():
                if f in val:
                    setattr(obj, f, val[f])

        obj.save()

    return obj


def import_from_json(model, data):
    if isinstance(data, dict):
        data = [data]

    created_objects = []
    activate("en")
    for entry in data:
        # lookup via unique constraint
        lookup = get_unique_lookup(model, entry)
        if not lookup:
            # fallback sur les champs simples
            lookup = {
                f.name: entry[f.name]
                for f in model._meta.get_fields()
                if f.name in entry
                and not (f.many_to_many or f.one_to_many or f.many_to_one)
            }

        obj = model.objects.create(**lookup)

        # Traduction
        if isinstance(obj, TranslatableModel):
            obj.set_current_language("en")
            for f in obj._parler_meta.get_translated_fields():
                if f in entry:
                    setattr(obj, f, entry[f])

        # normak field and FK
        for field in model._meta.get_fields():
            fname = field.name
            if fname in lookup or fname not in entry:
                continue

            value = entry[fname]

            if isinstance(field, models.ForeignKey):
                related_model = field.related_model
                rel_obj = get_or_create_related(related_model, value)
                setattr(obj, fname, rel_obj)
            elif not field.many_to_many and not field.one_to_many:
                setattr(obj, fname, value)

        obj.save()

        # manage m2m after save
        for field in model._meta.many_to_many:
            fname = field.name
            if fname not in entry:
                continue

            value = entry[fname]
            related_model = field.related_model
            rel_objs = [get_or_create_related(related_model, v) for v in value]
            obj.save()
            getattr(obj, fname).set(rel_objs)

        obj.save()
        obj.refresh_from_db()

        created_objects.append(obj)

    return created_objects


def initialize_user(users):
    for user in users:
        user.accepted_terms_date = timezone.now()
        user.save()


def link_entity_user(raw_data, created_users):
    for user in raw_data:
        if "email" in user:
            user_db = User.objects.filter(email=user["email"]).first()
            if "companies" in user and user_db:
                for c in user["companies"]:
                    if "identifier" in c:
                        company_db = Company.objects.get(identifier=c["identifier"])
                        user_db.companies.add(company_db)
                user_db.save()


@pytest.fixture
def otp_client(client):
    """
    Fixture to emulate 2FA connection
    """
    from django_otp import devices_for_user
    from django_otp.middleware import OTPMiddleware
    from django_otp.plugins.otp_static.models import StaticDevice

    def _login(user):
        client.force_login(user)
        devices = list(devices_for_user(user))
        # get or create the devices
        if devices:
            device = devices[0]
        else:
            device = StaticDevice.objects.create(user=user, name="test-device")
        session = client.session
        session["otp_device_id"] = device.persistent_id
        session.save()
        request = client.request().wsgi_request
        OTPMiddleware(lambda r: r)(request)
        request.user.otp_device = device
        return client

    return _login

import pytest
from django.db import models
from django.utils.translation import activate
from governanceplatform.models import (
    Company,
    Regulator,
    Observer,
    EntityCategory,
    Functionality
)
from governanceplatform.tests.data import (
    companies_data,
    regulators_data,
    functionalities_data,
    observers_data,
)
from parler.models import TranslatableModel


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

    return {
        "companies": created_companies,
        "functionnalities": created_functionalities,
        "regulators": created_regulators,
        "observers": created_observers,
        "entity_categories": [entity_category],
    }


def get_unique_lookup(model, data: dict):
    # make lookup on unique constraint excluding relational field
    unique_fields = []
    for constraint in model._meta.constraints:
        if isinstance(constraint, models.UniqueConstraint):
            unique_fields.extend(constraint.fields)

    simple_fields = [
        f.name for f in model._meta.get_fields()
        if not (f.many_to_many or f.one_to_many or f.is_relation)
    ]

    lookup = {f: data[f] for f in unique_fields if f in data and f in simple_fields}
    return lookup


def get_or_create_related(related_model, val: dict):
    if not isinstance(val, dict):
        raise ValueError(f"Unexpected value {related_model.__name__}: {val}")

    lookup = get_unique_lookup(related_model, val)
    if not lookup:
        raise ValueError(
            f"Unexpected lookup for {related_model.__name__} with data={val}"
        )

    obj, created = related_model.objects.get_or_create(**lookup)

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

    for entry in data:
        # lookup via unique constraint
        lookup = get_unique_lookup(model, entry)
        if not lookup:
            # fallback sur les champs simples
            lookup = {
                f.name: entry[f.name]
                for f in model._meta.get_fields()
                if f.name in entry and not (f.many_to_many or f.one_to_many or f.many_to_one)
            }

        obj, created = model.objects.get_or_create(**lookup)

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
            getattr(obj, fname).set(rel_objs)

        created_objects.append(obj)

    return created_objects

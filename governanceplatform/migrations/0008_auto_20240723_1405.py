from django.core.exceptions import ObjectDoesNotExist
from django.db import migrations


def forwards_func(apps, schema_editor):
    Regulator = apps.get_model("governanceplatform", "Regulator")
    RegulatorTranslation = apps.get_model("governanceplatform", "RegulatorTranslation")

    for object in Regulator.objects.all():
        RegulatorTranslation.objects.create(
            master_id=object.pk,
            language_code="en",
            name=object.temp_name,
            full_name=object.temp_full_name,
            description=object.temp_description,
        )


def backwards_func(apps, schema_editor):
    Regulator = apps.get_model("governanceplatform", "Regulator")
    RegulatorTranslation = apps.get_model("governanceplatform", "RegulatorTranslation")

    for object in Regulator.objects.all():
        translation = _get_translation(object, RegulatorTranslation)
        object.name = translation.name
        object.full_name = translation.full_name
        object.description = translation.description
        object.save()


def _get_translation(object, RegulatorTranslation):
    translations = RegulatorTranslation.objects.filter(master_id=object.pk)
    try:
        return translations.get(language_code="en")
    except ObjectDoesNotExist:
        return translations.get()


class Migration(migrations.Migration):
    dependencies = [
        ("governanceplatform", "0007_remove_regulator_description_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards_func, backwards_func),
    ]

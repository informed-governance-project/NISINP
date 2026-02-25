from django.core.exceptions import ObjectDoesNotExist
from django.db import migrations


def migrate_missing_entities(apps, schema_editor):
    LogReportRead = apps.get_model("incidents", "LogReportRead")
    ObserverTranslation = apps.get_model("governanceplatform", "ObserverTranslation")

    for log in LogReportRead.objects.all():
        if (log.entity_name == "" or log.entity_name is None) and log.user is not None:
            user = log.user
            observer = user.observers.first()
            if observer is not None:
                translation = _get_translation(observer, ObserverTranslation)
                log.entity_name = translation.name
                log.save()


def _get_translation(object, ObserverTranslation):
    translations = ObserverTranslation.objects.filter(master_id=object.pk)
    try:
        return translations.get(language_code="en")
    except ObjectDoesNotExist:
        return translations.get()


class Migration(migrations.Migration):

    dependencies = [
        ("incidents", "0054_incident_incident_last_update"),
    ]

    operations = [
        migrations.RunPython(migrate_missing_entities),
    ]

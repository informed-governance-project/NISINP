# Generated by Django 5.1.2 on 2024-11-28 12:03

from django.db import migrations, models


def delete_some_rows(apps, scheme_editor):
    model = apps.get_model('reporting', 'ReportConfiguration')
    model.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        (
            "governanceplatform",
            "0036_alter_functionality_type_delete_sectorcompanycontact",
        ),
        ("reporting", "0007_observationrecommendation_is_generic"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="riskanalysisjson",
            name="data",
        ),
        migrations.AddField(
            model_name="observationrecommendation",
            name="sectors",
            field=models.ManyToManyField(
                to="governanceplatform.company", verbose_name="Sectors"
            ),
        ),
        migrations.RunPython(delete_some_rows),
        migrations.RenameModel("ReportConfiguration", "SectorReportConfiguration"),
        migrations.AddField(
            model_name="sectorreportconfiguration",
            name="sector",
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE,
                to="governanceplatform.sector",
                verbose_name="Sector",
            ),
            preserve_default=False,
        ),
    ]
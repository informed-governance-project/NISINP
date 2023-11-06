# Generated by Django 4.2 on 2023-11-03 12:01

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('incidents', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='answer',
            name='incident',
        ),
        migrations.AddField(
            model_name='answer',
            name='incident_workflow',
            field=models.ForeignKey(default='', on_delete=django.db.models.deletion.CASCADE, to='incidents.incidentworkflow'),
            preserve_default=False,
        ),
    ]

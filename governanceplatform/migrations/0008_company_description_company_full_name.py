# Generated by Django 4.2 on 2023-09-27 06:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('governanceplatform', '0007_rename_accronym_sector_acronym_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='description',
            field=models.TextField(blank=True, default='', null=True, verbose_name='description'),
        ),
        migrations.AddField(
            model_name='company',
            name='full_name',
            field=models.TextField(blank=True, default='', null=True, verbose_name='full name'),
        ),
    ]
# Generated by Django 4.2 on 2023-05-16 09:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('governanceplatform', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='company',
            old_name='adress',
            new_name='address',
        ),
        migrations.RenameField(
            model_name='sector',
            old_name='parent_id',
            new_name='parent',
        ),
        migrations.RemoveField(
            model_name='user',
            name='company',
        ),
        migrations.AddField(
            model_name='company',
            name='sectors',
            field=models.ManyToManyField(to='governanceplatform.sector'),
        ),
        migrations.AddField(
            model_name='user',
            name='companies',
            field=models.ManyToManyField(to='governanceplatform.company'),
        ),
        migrations.AddField(
            model_name='user',
            name='sectors',
            field=models.ManyToManyField(to='governanceplatform.sector'),
        ),
    ]

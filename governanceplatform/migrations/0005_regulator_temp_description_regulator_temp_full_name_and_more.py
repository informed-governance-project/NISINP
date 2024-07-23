# Generated by Django 5.0.7 on 2024-07-23 11:59

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("governanceplatform", "0004_alter_certuser_cert_alter_certuser_user_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="regulator",
            name="temp_description",
            field=models.TextField(
                blank=True, default="", null=True, verbose_name="temp_description"
            ),
        ),
        migrations.AddField(
            model_name="regulator",
            name="temp_full_name",
            field=models.TextField(
                blank=True, default="", null=True, verbose_name="temp_full name"
            ),
        ),
        migrations.AddField(
            model_name="regulator",
            name="temp_name",
            field=models.CharField(default="", max_length=64, verbose_name="temp_name"),
        ),
    ]
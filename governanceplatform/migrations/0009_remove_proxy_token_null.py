from django.db import migrations, models

import governanceplatform.helpers


class Migration(migrations.Migration):

    dependencies = [
        ("governanceplatform", "0008_populate_uuid_values"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="proxy_token",
            field=models.CharField(
                default=governanceplatform.helpers.generate_token,
                max_length=255,
                unique=True,
            ),
        ),
    ]

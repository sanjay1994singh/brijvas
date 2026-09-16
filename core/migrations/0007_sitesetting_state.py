from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_alter_contact_id_alter_sitesetting_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesetting",
            name="state",
            field=models.CharField(blank=True, max_length=100),
        ),
    ]

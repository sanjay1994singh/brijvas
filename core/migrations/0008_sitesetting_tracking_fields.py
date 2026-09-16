from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_sitesetting_state"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesetting",
            name="google_analytics_id",
            field=models.CharField(blank=True, max_length=40),
        ),
        migrations.AddField(
            model_name="sitesetting",
            name="google_ads_id",
            field=models.CharField(blank=True, max_length=40),
        ),
        migrations.AddField(
            model_name="sitesetting",
            name="google_site_verification",
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AddField(
            model_name="sitesetting",
            name="custom_head_scripts",
            field=models.TextField(blank=True),
        ),
    ]

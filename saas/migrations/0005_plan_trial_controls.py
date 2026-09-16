from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("saas", "0004_billingorder_failed_webhookevent"),
    ]

    operations = [
        migrations.AddField(
            model_name="plan",
            name="trial_enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="plan",
            name="trial_days",
            field=models.PositiveIntegerField(default=7),
        ),
    ]

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('saas', '0013_fix_stale_pending_vrinda'),
    ]

    operations = [
        migrations.AddField(
            model_name='billingorder',
            name='billing_months',
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='pendingsignup',
            name='billing_months',
            field=models.PositiveSmallIntegerField(default=1),
        ),
    ]

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("saas", "0011_purchase_agreement"),
    ]

    operations = [
        migrations.AddField(
            model_name="pendingsignup",
            name="password_hash",
            field=models.CharField(blank=True, max_length=128),
        ),
    ]

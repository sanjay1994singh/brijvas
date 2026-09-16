import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("saas", "0006_planfeature_seed_pricing"),
    ]

    operations = [
        migrations.CreateModel(
            name="PendingSignup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("business_name", models.CharField(max_length=160)),
                ("username", models.CharField(max_length=150)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("phone", models.CharField(max_length=20)),
                ("state", models.CharField(blank=True, max_length=100)),
                ("amount", models.PositiveIntegerField()),
                ("currency", models.CharField(default="INR", max_length=3)),
                ("provider_order", models.CharField(blank=True, max_length=100, null=True, unique=True)),
                ("provider_payment", models.CharField(blank=True, max_length=100, null=True, unique=True)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("paid", "Paid"), ("failed", "Failed")], default="pending", max_length=16)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("paid_at", models.DateTimeField(blank=True, null=True)),
                ("plan", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="saas.plan")),
            ],
        ),
    ]

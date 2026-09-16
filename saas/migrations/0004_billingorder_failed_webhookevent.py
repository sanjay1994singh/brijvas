from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("saas", "0003_domain_is_platform_domain_last_attempt_at_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="billingorder",
            name="status",
            field=models.CharField(
                choices=[("pending", "Pending"), ("paid", "Paid"), ("failed", "Failed")],
                default="pending",
                max_length=12,
            ),
        ),
        migrations.CreateModel(
            name="WebhookEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider", models.CharField(default="razorpay", max_length=40)),
                ("event_id", models.CharField(max_length=120)),
                ("event_type", models.CharField(max_length=120)),
                ("payload", models.JSONField(default=dict)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("provider", "event_id"),
                        name="saas_unique_provider_webhook_event",
                    )
                ],
            },
        ),
    ]

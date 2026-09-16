from django.db import migrations, models
import django.db.models.deletion


PLAN_DEFAULTS = {
    "starter": {"amount": 39900, "listing_limit": 10, "staff_limit": 1},
    "agency": {"amount": 59900, "listing_limit": 25, "staff_limit": 3},
    "business": {"amount": 79900, "listing_limit": 50, "staff_limit": 5},
}


def seed_plan_settings(apps, schema_editor):
    Plan = apps.get_model("saas", "Plan")
    PlanFeature = apps.get_model("saas", "PlanFeature")
    for slug, values in PLAN_DEFAULTS.items():
        plan = Plan.objects.filter(slug=slug).first()
        if not plan:
            continue
        plan.monthly_amount = values["amount"]
        plan.listing_limit = values["listing_limit"]
        plan.staff_limit = values["staff_limit"]
        plan.custom_domain = True
        plan.storage_mb = 102400
        plan.save(update_fields=["monthly_amount", "listing_limit", "staff_limit", "custom_domain", "storage_mb"])
        defaults = [
            f"{values['listing_limit']} property listings",
            f"{values['staff_limit']} staff seats",
            "Custom domain support",
        ]
        for index, text in enumerate(defaults, start=1):
            PlanFeature.objects.get_or_create(plan=plan, text=text, defaults={"sort_order": index})


class Migration(migrations.Migration):

    dependencies = [
        ("saas", "0005_plan_trial_controls"),
    ]

    operations = [
        migrations.CreateModel(
            name="PlanFeature",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("text", models.CharField(max_length=160)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("plan", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="features", to="saas.plan")),
            ],
            options={"ordering": ["sort_order", "id"]},
        ),
        migrations.RunPython(seed_plan_settings, migrations.RunPython.noop),
    ]

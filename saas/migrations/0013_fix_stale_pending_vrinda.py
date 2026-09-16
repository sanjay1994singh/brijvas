from django.db import migrations


def fix_vrinda_workspace(apps, schema_editor):
    Tenant = apps.get_model("saas", "Tenant")
    Domain = apps.get_model("saas", "Domain")
    PendingSignup = apps.get_model("saas", "PendingSignup")
    User = apps.get_model("accounts", "User")

    PendingSignup.objects.filter(username="vrinda", status="pending").update(status="failed")
    if Tenant.objects.filter(slug="vrinda").exists():
        return
    tenant = Tenant.objects.filter(slug="vrinda-2", name__iexact="vrinda").first()
    if not tenant:
        return
    old_slug = tenant.slug
    tenant.slug = "vrinda"
    tenant.save(update_fields=["slug"])
    Domain.objects.filter(tenant=tenant, hostname=f"{old_slug}.live-app.in").update(hostname="vrinda.live-app.in")
    if tenant.owner_id:
        User.objects.filter(pk=tenant.owner_id, username=old_slug).update(username="vrinda")
    PendingSignup.objects.filter(username=old_slug, business_name__iexact="vrinda", status="paid").update(username="vrinda")


class Migration(migrations.Migration):

    dependencies = [
        ("saas", "0012_pendingsignup_password_hash"),
    ]

    operations = [
        migrations.RunPython(fix_vrinda_workspace, migrations.RunPython.noop),
    ]

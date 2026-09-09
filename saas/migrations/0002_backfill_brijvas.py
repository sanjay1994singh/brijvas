from datetime import timedelta
from django.db import migrations
from django.utils import timezone


def backfill(apps, schema_editor):
    alias = schema_editor.connection.alias
    Plan = apps.get_model('saas', 'Plan')
    Tenant = apps.get_model('saas', 'Tenant')
    Membership = apps.get_model('saas', 'Membership')
    Subscription = apps.get_model('saas', 'Subscription')
    SiteSetting = apps.get_model('core', 'SiteSetting')
    # Preserve all historical rows; don't guess which of multiple legacy settings to delete.
    if SiteSetting.objects.using(alias).filter(tenant__isnull=True).count() > 1:
        raise RuntimeError('Multiple legacy SiteSetting rows found. Reconcile them explicitly before SaaS migration.')
    for slug, name, listings, staff, storage, custom in [
        ('starter', 'Starter', 50, 3, 1024, False),
        ('agency', 'Agency', 250, 10, 5120, True),
        ('business', 'Business', 1000, 25, 20480, True),
    ]:
        Plan.objects.using(alias).get_or_create(slug=slug, defaults=dict(name=name, listing_limit=listings, staff_limit=staff, storage_mb=storage, custom_domain=custom))
    legacy_plan, _ = Plan.objects.using(alias).get_or_create(slug='legacy-brijvas', defaults=dict(name='Brijvas existing customer', listing_limit=100000, staff_limit=100000, storage_mb=102400, custom_domain=True, is_active=False))
    tenant, _ = Tenant.objects.using(alias).get_or_create(slug='brijvas', defaults={'name': 'Brij Vas', 'status': 'active'})
    Subscription.objects.using(alias).get_or_create(tenant=tenant, defaults={'plan': legacy_plan, 'is_trial': False, 'expires_at': timezone.now() + timedelta(days=36500)})
    for app, names in [('core', ['SiteSetting', 'Contact']), ('properties', ['Property', 'PropertyType', 'Amenity']), ('blog', ['Blog', 'BlogCategory'])]:
        for name in names:
            apps.get_model(app, name).objects.using(alias).filter(tenant__isnull=True).update(tenant=tenant)
    SiteSetting.objects.using(alias).get_or_create(tenant=tenant, defaults={'site_name': 'Brij Vas', 'email': '', 'phone': '', 'whatsapp': '', 'address': '', 'about_text': 'Brij Vas property services.'})
    for user in apps.get_model('accounts', 'User').objects.using(alias).iterator():
        role = 'admin' if user.is_superuser else {'owner': 'seller', 'agent': 'agent'}.get(user.user_type, 'buyer')
        Membership.objects.using(alias).get_or_create(tenant=tenant, user=user, defaults={'role': role, 'is_active': user.is_active, 'is_approved': user.is_superuser or user.is_verified or role == 'buyer'})


class Migration(migrations.Migration):
    dependencies = [
        ('saas', '0001_initial'),
        ('core', '0003_contact_tenant_sitesetting_about_text_and_more'),
        ('properties', '0009_amenity_tenant_property_tenant_propertytype_tenant_and_more'),
        ('blog', '0006_blog_tenant_blogcategory_tenant_and_more'),
    ]
    # Deliberately irreversible: reversing ownership after multiple tenants exist is unsafe.
    operations = [migrations.RunPython(backfill)]

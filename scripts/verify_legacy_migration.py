"""Rehearse the old Brijvas schema -> SaaS schema using synthetic in-memory data."""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['DJANGO_SETTINGS_MODULE'] = 'brijvas.settings_test'
import django
django.setup()
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

assert connection.settings_dict['ENGINE'] == 'django.db.backends.sqlite3'
assert connection.settings_dict['NAME'] == ':memory:'
executor = MigrationExecutor(connection)
legacy = [('accounts', '0003_user_address_user_city_user_country_user_state'), ('properties', '0008_property_more_area_units'), ('blog', '0005_blogview'), ('core', '0002_contact'), ('enquiries', '0001_initial'), ('locations', '0002_auto_slug_blank')]
executor.migrate(legacy)
apps = executor.loader.project_state(legacy).apps
User = apps.get_model('accounts', 'User')
user = User.objects.create(username='legacy-seller', user_type='owner', is_verified=True)
state = apps.get_model('locations', 'State').objects.create(name='UP', slug='up')
city = apps.get_model('locations', 'City').objects.create(name='Mathura', slug='mathura', state=state)
category = apps.get_model('properties', 'PropertyType').objects.create(name='Plot', slug='plot', image='property-types/old.jpg')
prop = apps.get_model('properties', 'Property').objects.create(user=user, property_type=category, state=state, city=city, title='Legacy listing', slug='legacy-listing', purpose='sale', price=1000, area=100, featured_image='properties/legacy.jpg')
lead = apps.get_model('enquiries', 'Enquiry').objects.create(property=prop, name='Legacy lead', email='test@example.test', phone='1234567890', message='Preserve this message')
apps.get_model('core', 'SiteSetting').objects.create(site_name='Brij Vas', email='test@example.test', phone='1234567890', whatsapp='911234567890', address='Old address', logo='settings/old-logo.jpg', favicon='settings/old-icon.png')
executor = MigrationExecutor(connection)
executor.migrate(executor.loader.graph.leaf_nodes())
from properties.models import Property
from enquiries.models import Enquiry
from core.models import SiteSetting
from saas.models import Tenant, Membership
tenant = Tenant.objects.get(slug='brijvas')
migrated = Property.objects.get(pk=prop.pk)
assert migrated.tenant_id == tenant.pk
assert migrated.slug == 'legacy-listing'
assert migrated.featured_image.name == 'properties/legacy.jpg'
assert Enquiry.objects.get(pk=lead.pk).message == 'Preserve this message'
assert SiteSetting.objects.get(tenant=tenant).logo.name == 'settings/old-logo.jpg'
member = Membership.objects.get(tenant=tenant, user_id=user.pk)
assert member.role == 'seller' and member.is_approved
assert Property.objects.filter(tenant__isnull=True).count() == 0
print('PASS: legacy IDs, slugs, images, enquiry and approved seller preserved by SaaS migration.')

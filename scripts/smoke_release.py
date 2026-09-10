"""Read-only production-shape HTTP checks before switching traffic."""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'brijvas.settings')
import django
django.setup()
from django.conf import settings
from urllib.parse import urlsplit
from django.test import Client
from properties.models import Property
from saas.models import Tenant
from core.models import SiteSetting

client = Client(HTTP_HOST='brijvas.com', HTTP_X_FORWARDED_PROTO='https')
tenant = Tenant.objects.get(slug='brijvas')
assert Property.objects.filter(tenant__isnull=True).count() == 0
assert SiteSetting.objects.filter(tenant=tenant).count() == 1
paths = ['/', '/properties/', '/blog/', '/about/', '/contact/', '/sitemap.xml']
property_obj = Property.objects.filter(tenant=tenant, is_active=True).first()
if property_obj:
    paths.append(property_obj.get_absolute_url())
for path in paths:
    response = client.get(path)
    assert response.status_code == 200, (path, response.status_code)
    print('PASS', path)
platform = Client(HTTP_HOST=urlsplit(settings.SAAS_BASE_URL).netloc, HTTP_X_FORWARDED_PROTO='https')
for path in ['/', '/saas/', '/saas/signup/', '/saas/login/']:
    assert platform.get(path).status_code == 200, path
    print('PASS platform', path)
print('Release smoke checks passed; property count:', Property.objects.filter(tenant=tenant).count())

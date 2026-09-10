from types import SimpleNamespace
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from .models import Domain, Tenant
from .services import provision
from .tests import TwoBusinessFixture
from .domain_provisioning import check_dns, http_config, https_config


class AutomaticDomainTests(TwoBusinessFixture, TestCase):
    @override_settings(SAAS_AUTO_DOMAINS=True, SAAS_USE_PATH_URLS=True, SAAS_CUSTOMER_DOMAIN_ROOT='localhost')
    def test_brand_name_and_collision_create_pending_https_addresses(self):
        users = [get_user_model().objects.create_user(username=f'brand{i}') for i in range(2)]
        tenants = [provision(owner=user, name='Sharma Realty', plan=self.plan) for user in users]
        self.assertEqual([t.slug for t in tenants], ['sharmarealty', 'sharmarealty-2'])
        domain = tenants[0].domains.get()
        self.assertEqual(domain.hostname, 'sharmarealty.localhost')
        self.assertTrue(domain.is_platform and domain.is_verified and domain.provisioning_requested)
        self.assertFalse(domain.ssl_ready)
        self.assertEqual(tenants[0].public_url, 'http://localhost/sites/sharmarealty')
        domain.ssl_ready = domain.is_primary = True
        domain.save()
        self.assertEqual(tenants[0].public_url, 'https://sharmarealty.localhost')

    @override_settings(SAAS_BASE_URL='https://propertystudio.live-app.in', SAAS_CUSTOMER_DOMAIN_ROOT='live-app.in',
                       SAAS_AUTO_DOMAINS=True, SAAS_USE_PATH_URLS=False)
    def test_customer_subdomain_uses_root_domain_separate_from_portal(self):
        user = get_user_model().objects.create_user(username='directroot')
        tenant = provision(owner=user, name='Green Acre Homes', plan=self.plan)
        self.assertEqual(tenant.slug, 'greenacrehomes')
        self.assertEqual(tenant.domains.get().hostname, 'greenacrehomes.live-app.in')
        self.assertEqual(tenant.public_url, 'https://greenacrehomes.live-app.in')

    @override_settings(ALLOWED_HOSTS=['*'])
    def test_dynamic_custom_host_guard_rejects_unverified_and_unknown_hosts(self):
        domain = Domain.objects.create(tenant=self.ta, hostname='brand.example.com')
        self.assertEqual(self.get('/', host=domain.hostname).status_code, 400)
        domain.is_verified = domain.ssl_ready = True
        domain.save()
        self.assertContains(self.get('/', host=domain.hostname), 'Sunrise Realty')
        self.assertEqual(self.get('/', host='untrusted.example.com').status_code, 400)

    @override_settings(SAAS_SERVER_IP='103.168.19.9')
    def test_dns_requires_platform_ip_and_ownership(self):
        import dns.resolver
        domain = Domain.objects.create(tenant=self.ta, hostname='brand.example.com')
        def resolver(name, kind, **kwargs):
            if kind == 'A': return ['103.168.19.9']
            if kind == 'AAAA': raise dns.resolver.NoAnswer()
            return [SimpleNamespace(strings=[domain.txt_value.encode()])]
        with patch('saas.domain_provisioning.dns.resolver.resolve', side_effect=resolver):
            check_dns(domain)
        with patch('saas.domain_provisioning.dns.resolver.resolve', return_value=['127.0.0.1']):
            with self.assertRaises(ValidationError): check_dns(domain)
        self.assertIn('ServerName brand.example.com', http_config(domain.hostname))
        self.assertIn('/live/property-domain-123/', https_config(domain.hostname, 'property-domain-123'))
        with self.assertRaises(ValidationError): http_config('bad.com\nServerAlias *')

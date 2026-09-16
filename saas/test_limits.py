from unittest.mock import patch
from django.urls import reverse
from django.core.exceptions import PermissionDenied
from django.test import TestCase, override_settings
from .tests import TwoBusinessFixture, photo
from .models import Membership
from .services import save_listing
from properties.forms import PropertyForm


class LimitAndWriteTests(TwoBusinessFixture, TestCase):
    """Additional write-path checks reuse the two-business fixture."""

    def test_tenant_management_moves_to_platform_host(self):
        response = self.get('/accounts/login/?next=/accounts/workspaces/')
        self.assertEqual(response.url, 'http://localhost/accounts/login/?next=/accounts/workspaces/')
        self.assertEqual(self.get('/admin/').url, 'http://localhost/admin/')
        self.assertEqual(self.post('/accounts/signup/').status_code, 403)
        self.assertContains(self.get('/', host='localhost'), 'Vistaflo')

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend', EMAIL_HOST='')
    def test_unconfigured_recovery_is_explicit_and_does_not_send(self):
        response = self.get('/accounts/password-reset/', host='localhost')
        self.assertContains(response, 'Email recovery is not available yet', status_code=503)

    def test_password_recovery_templates_and_email(self):
        from django.core import mail
        self.assertEqual(self.get('/accounts/password-reset/').status_code, 200)
        self.assertEqual(self.post('/accounts/password-reset/', {'email': self.a.email}).status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('/accounts/reset/', mail.outbox[0].body)
        self.assertEqual(self.get('/accounts/password-reset/done/').status_code, 200)
        self.assertEqual(self.get('/accounts/reset/invalid/invalid/').status_code, 200)
        self.assertEqual(self.get('/accounts/reset-complete/').status_code, 200)

    def test_generated_description_strips_untrusted_business_markup(self):
        self.ta.name = '<img src=x onerror=alert(1)>Business'
        self.ta.save()
        self.pa.tenant = self.ta
        self.pa.description = ''
        self.pa.save()
        self.pa.refresh_from_db()
        self.assertNotIn('onerror', self.pa.description)
        self.assertIn('Business', self.pa.description)

    @override_settings(SAAS_USE_PATH_URLS=True, SAAS_ROOT_TENANT='brijvas')
    def test_path_sites_keep_navigation_and_isolation(self):
        response = self.get('/sites/sunrise/', host='localhost')
        self.assertContains(response, '/sites/sunrise/properties/search/')
        self.assertContains(response, 'Sunrise Realty')
        self.assertNotContains(response, self.pb.title)
        self.assertEqual(self.ta.public_url, 'http://localhost/sites/sunrise')
        self.client.force_login(self.a)
        self.assertEqual(self.get('/sites/sunrise/dashboard/', host='localhost').status_code, 200)
        self.assertEqual(self.get('/sites/cedar/dashboard/', host='localhost').status_code, 403)
        self.assertContains(self.get('/', host='localhost'), 'Vistaflo')

    @override_settings(SAAS_USE_PATH_URLS=True, SAAS_ROOT_TENANT='brijvas')
    def test_platform_login_does_not_require_legacy_membership(self):
        response = self.post('/accounts/login/', {'username': self.a.username, 'password': 'Strong-Test-Pass-672!'}, host='localhost')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/accounts/workspaces/')

    def test_storage_limit_blocks_editor_and_listing_upload(self):
        self.plan.storage_mb = 0
        self.plan.save()
        self.client.force_login(self.a)
        self.assertEqual(self.post('/ckeditor5/image_upload/', {'upload': photo()}).status_code, 400)
        response = self.post(reverse('add_property'), {'property_type': self.pa.property_type_id, 'purpose': 'sale', 'state': self.state.pk, 'city': self.city.pk, 'price': 100, 'area': 100, 'area_unit': 'sqft', 'featured_image': photo()})
        self.assertContains(response, 'storage limit')

    def test_approved_owner_can_create_and_edit_property(self):
        self.client.force_login(self.a)
        result = self.post(reverse('add_property'), {'property_type': self.pa.property_type_id, 'purpose': 'sale', 'state': self.state.pk, 'city': self.city.pk, 'price': 100, 'area': 100, 'area_unit': 'sqft', 'featured_image': photo()})
        self.assertEqual(result.status_code, 302)
        result = self.get(reverse('edit_property', args=[self.pa.pk]))
        self.assertEqual(result.status_code, 200)

    def test_stale_membership_cannot_bypass_service(self):
        member = self.ta.memberships.get(user=self.a)
        Membership.objects.filter(pk=member.pk).update(is_active=False)
        form = PropertyForm(instance=self.pa, tenant=self.ta)
        with self.assertRaises(PermissionDenied):
            save_listing(form=form, tenant=self.ta, user=self.a, membership=member)

    def test_member_staff_quota_blocks_promotion(self):
        Membership.objects.create(tenant=self.ta, user=self.b, role='buyer', is_approved=True)
        self.plan.staff_limit = 1
        self.plan.save()
        self.client.force_login(self.a)
        response = self.post(reverse('saas_members', args=['sunrise']), {'username': self.b.username, 'role': 'agent'}, host='localhost')
        self.assertContains(response, 'staff limit')
        self.assertEqual(Membership.objects.get(tenant=self.ta, user=self.b).role, 'buyer')

    def test_branding_updates_only_current_business(self):
        from core.models import SiteSetting
        self.client.force_login(self.a)
        response = self.post(reverse('saas_branding', args=['sunrise']), {'site_name': 'New Sunrise', 'tagline': 'Your new home', 'email': 'hello@example.test', 'phone': '1234567890', 'whatsapp': '911234567890', 'address': 'Example street', 'primary_color': '#126a45', 'about_text': 'A local business.'}, host='localhost')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(SiteSetting.objects.get(tenant=self.ta).site_name, 'New Sunrise')
        self.assertEqual(SiteSetting.objects.get(tenant=self.tb).site_name, 'Cedar Homes')

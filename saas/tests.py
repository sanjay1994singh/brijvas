from datetime import timedelta
from io import BytesIO
import hashlib
import hmac
import json
import tempfile
from unittest.mock import patch

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings, Client
from django.urls import reverse
from django.utils import timezone

from core.models import SiteSetting, Contact
from properties.models import Property, PropertyType, CompareProperty, Wishlist
from properties.forms import PropertyForm
from blog.models import Blog, BlogCategory
from locations.models import State, City
from enquiries.models import Enquiry
from .models import BillingOrder, Domain, Membership, Plan, Tenant
from .services import provision, save_listing
from .scoping import scoped
from . import billing


def photo():
    stream = BytesIO()
    Image.new('RGB', (20, 20), 'green').save(stream, 'JPEG')
    return SimpleUploadedFile('house.jpg', stream.getvalue(), content_type='image/jpeg')


class TwoBusinessFixture:
    def setUp(self):
        self.media = tempfile.TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        self.override = override_settings(MEDIA_ROOT=self.media.name)
        self.override.enable()
        self.addCleanup(self.override.disable)
        User = get_user_model()
        self.a = User.objects.create_user(username='alice', password='Strong-Test-Pass-672!', email='alice@example.test')
        self.b = User.objects.create_user(username='bob', password='Strong-Test-Pass-672!', email='bob@example.test')
        self.plan = Plan.objects.get(slug='agency')
        self.ta = provision(owner=self.a, name='Sunrise Realty', slug='sunrise', plan=self.plan)
        self.tb = provision(owner=self.b, name='Cedar Homes', slug='cedar', plan=self.plan)
        self.state = State.objects.create(name='Uttar Pradesh')
        self.city = City.objects.create(name='Mathura', state=self.state)
        self.pa = self.make_property(self.ta, self.a, 'Sunrise unique villa')
        self.pb = self.make_property(self.tb, self.b, 'Cedar exclusive plot')

    def make_property(self, tenant, user, title):
        return Property.objects.create(tenant=tenant, user=user, title=title, property_type=PropertyType.objects.filter(tenant=tenant).first(), state=self.state, city=self.city, purpose='sale', price=1500000, area=100, featured_image=photo())

    def get(self, path, host='sunrise.localhost'):
        return self.client.get(path, HTTP_HOST=host)

    def post(self, path, data=None, host='sunrise.localhost'):
        return self.client.post(path, data or {}, HTTP_HOST=host)


class SaasTests(TwoBusinessFixture, TestCase):
    def test_platform_and_all_customer_screens_render(self):
        self.assertEqual(self.get('/', 'localhost').status_code, 200)
        self.assertEqual(self.get('/accounts/signup/', 'localhost').status_code, 200)
        for path in ['/', '/properties/', '/blog/', '/about/', '/contact/', '/accounts/login/', '/accounts/register/', '/sitemap.xml', '/robots.txt']:
            with self.subTest(path=path):
                self.assertEqual(self.get(path).status_code, 200)
        self.client.force_login(self.a)
        for name in ['saas_business', 'saas_branding', 'saas_members', 'saas_domains', 'saas_listings', 'saas_leads']:
            with self.subTest(name=name):
                self.assertEqual(self.get(reverse(name, args=['sunrise']), 'localhost').status_code, 200)

    def test_home_listing_search_detail_sitemap_isolation(self):
        for path in ['/', '/properties/', '/properties/search/', '/sitemap.xml']:
            response = self.get(path)
            self.assertNotContains(response, self.pb.title)
            self.assertNotContains(response, self.pb.slug)
        self.assertContains(self.get(self.pa.get_absolute_url()), self.pa.title)
        self.assertNotEqual(self.get(self.pb.get_absolute_url()).status_code, 200)

    def test_same_slug_allowed_in_different_tenants(self):
        self.pb.slug = self.pa.slug
        self.pb.save()
        self.assertContains(self.get(self.pa.get_absolute_url()), self.pa.title)
        self.assertContains(self.get(self.pb.get_absolute_url(), 'cedar.localhost'), self.pb.title)

    def test_slug_uniqueness_is_enforced_by_database(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            PropertyType.objects.create(tenant=self.ta, name='Other', slug=PropertyType.objects.filter(tenant=self.ta).first().slug)

    def test_missing_context_returns_no_data(self):
        self.assertFalse(scoped(Property, None).exists())
        self.assertFalse(scoped(Enquiry, None).exists())

    def test_unknown_and_unverified_domains_fail_closed(self):
        self.assertEqual(self.get('/', 'unknown.localhost').status_code, 404)
        Domain.objects.create(tenant=self.ta, hostname='customer.example.test')
        self.assertEqual(self.get('/', 'customer.example.test').status_code, 404)
        self.ta.status = 'suspended'
        self.ta.save()
        self.assertEqual(self.get('/').status_code, 403)

    def test_verified_tls_domain_routes_tenant(self):
        Domain.objects.create(tenant=self.ta, hostname='customer.example.test', is_verified=True, ssl_ready=True, is_primary=True)
        self.assertContains(self.get('/', 'customer.example.test'), 'Sunrise Realty')

    def test_cross_tenant_dashboard_and_management_are_denied(self):
        self.client.force_login(self.a)
        self.assertEqual(self.get('/dashboard/', 'cedar.localhost').status_code, 403)
        self.assertEqual(self.get(reverse('saas_business', args=['cedar']), 'localhost').status_code, 403)
        self.assertEqual(self.post(reverse('delete_property', args=[self.pb.pk])).status_code, 404)
        self.assertTrue(Property.objects.filter(pk=self.pb.pk).exists())

    def test_customer_admin_is_not_platform_admin(self):
        self.a.is_staff = True
        self.a.save()
        self.client.force_login(self.a)
        self.assertEqual(self.get('/admin/', 'localhost').status_code, 403)
        self.assertEqual(self.get('/admin/').status_code, 403)

    def test_foreign_category_is_rejected(self):
        form = PropertyForm(data={'property_type': self.pb.property_type_id, 'purpose': 'sale', 'state': self.state.pk, 'city': self.city.pk, 'price': 20, 'area': 100, 'area_unit': 'sqft'}, files={'featured_image': photo()}, tenant=self.ta)
        self.assertFalse(form.is_valid())
        self.assertIn('property_type', form.errors)
        self.pa.property_type = self.pb.property_type
        with self.assertRaises(ValidationError):
            self.pa.save()

    def test_signup_provisions_complete_independent_site(self):
        result = self.post('/accounts/signup/', {'business_name': 'New Realty', 'site_slug': 'new-realty', 'username': 'newowner', 'email': 'new@example.test', 'phone': '', 'plan': self.plan.pk, 'password1': 'Distant-Orange-7284!', 'password2': 'Distant-Orange-7284!'}, host='localhost')
        self.assertEqual(result.status_code, 302)
        tenant = Tenant.objects.get(slug='newrealty')
        self.assertTrue(tenant.memberships.get().can_manage)
        self.assertEqual(Property.objects.filter(tenant=tenant).count(), 0)
        self.assertEqual(PropertyType.objects.filter(tenant=tenant).count(), 5)
        self.assertEqual(SiteSetting.objects.get(tenant=tenant).site_name, 'New Realty')
        self.assertTrue(tenant.subscription.usable)

    def test_provision_failure_rolls_back_everything(self):
        user = get_user_model().objects.create_user(username='third')
        before = Tenant.objects.count()
        with patch('properties.models.PropertyType.objects.get_or_create', side_effect=RuntimeError('seed failed')):
            with self.assertRaises(RuntimeError):
                provision(owner=user, name='Failure', slug='failure', plan=self.plan)
        self.assertEqual(Tenant.objects.count(), before)
        self.assertFalse(user.memberships.exists())

    def test_existing_slug_cannot_grant_membership(self):
        with self.assertRaises(ValidationError):
            provision(owner=self.b, name='Hijack', slug='sunrise', plan=self.plan)
        self.assertFalse(self.ta.memberships.filter(user=self.b).exists())

    def test_registered_seller_cannot_self_approve(self):
        result = self.post('/accounts/register/', {'first_name': 'Seller', 'username': 'sellerone', 'email': 'seller@example.test', 'phone': '', 'user_type': 'owner', 'password1': 'Distant-Orange-7284!', 'password2': 'Distant-Orange-7284!', 'is_verified': True, 'is_staff': True})
        self.assertEqual(result.status_code, 302)
        member = Membership.objects.get(user__username='sellerone')
        self.assertEqual(member.role, 'seller')
        self.assertFalse(member.can_list)

    def test_foreign_login_and_external_next_are_rejected(self):
        self.post('/accounts/login/', {'username': 'bob', 'password': 'Strong-Test-Pass-672!'})
        self.assertNotIn('_auth_user_id', self.client.session)
        result = self.post('/accounts/login/?next=https://evil.example/', {'username': 'alice', 'password': 'Strong-Test-Pass-672!'})
        self.assertEqual(result.url, '/dashboard/')

    def test_contact_is_saved_to_correct_tenant(self):
        result = self.post('/contact/', {'name': 'Interested buyer', 'email': 'buyer@example.test', 'phone': '', 'subject': 'Site visit', 'message': 'Please contact me'})
        self.assertEqual(result.status_code, 302)
        self.assertEqual(Contact.objects.get(name='Interested buyer').tenant_id, self.ta.pk)

    def test_enquiry_is_not_visible_to_another_business(self):
        Enquiry.objects.create(property=self.pb, name='Confidential lead', email='lead@example.test', phone='1234567890', message='Private details')
        self.client.force_login(self.a)
        self.assertNotContains(self.get(reverse('saas_leads', args=['sunrise']), 'localhost'), 'Confidential lead')

    def test_delete_requires_post_and_csrf(self):
        self.client.force_login(self.a)
        path = reverse('delete_property', args=[self.pa.pk])
        self.assertEqual(self.get(path).status_code, 405)
        secure_client = Client(enforce_csrf_checks=True)
        secure_client.force_login(self.a)
        self.assertEqual(secure_client.post(path, HTTP_HOST='sunrise.localhost').status_code, 403)

    def test_listing_limit_and_expiry_enforced(self):
        self.plan.listing_limit = 1
        self.plan.save()
        form = PropertyForm(data={'property_type': self.pa.property_type_id, 'purpose': 'sale', 'state': self.state.pk, 'city': self.city.pk, 'price': 20, 'area': 100, 'area_unit': 'sqft'}, files={'featured_image': photo()}, tenant=self.ta)
        self.assertTrue(form.is_valid(), form.errors)
        with self.assertRaises(ValidationError):
            save_listing(form=form, tenant=self.ta, user=self.a, membership=self.ta.memberships.get(user=self.a))
        sub = self.ta.subscription
        sub.expires_at = timezone.now() - timedelta(days=1)
        sub.save()
        self.plan.listing_limit = 10
        self.plan.save()
        with self.assertRaises(ValidationError):
            save_listing(form=form, tenant=self.ta, user=self.a, membership=self.ta.memberships.get(user=self.a))

    def test_editor_upload_requires_approved_member(self):
        self.client.force_login(self.b)
        self.assertEqual(self.post('/ckeditor5/image_upload/', {'upload': photo()}).status_code, 403)
        self.client.force_login(self.a)
        response = self.post('/ckeditor5/image_upload/', {'upload': photo()})
        self.assertEqual(response.status_code, 200)
        self.assertIn(str(self.ta.uuid), response.json()['url'])

    def test_compare_and_wishlist_scope(self):
        self.client.force_login(self.a)
        CompareProperty.objects.create(user=self.a, property=self.pb)
        Wishlist.objects.create(user=self.a, property=self.pb)
        self.assertNotContains(self.get(reverse('wishlist')), self.pb.title)
        self.assertEqual(self.post(reverse('add_to_compare', args=[self.pb.pk])).status_code, 404)

    def test_blogs_do_not_mix(self):
        category = BlogCategory.objects.create(tenant=self.tb, name='Cedar news')
        post = Blog.objects.create(tenant=self.tb, category=category, author=self.b, title='Cedar confidential blog', content='Example', featured_image=photo())
        self.assertNotContains(self.get('/blog/'), post.title)
        self.assertEqual(self.get(post.get_absolute_url()).status_code, 404)

    @override_settings(RAZORPAY_KEY_SECRET='test-secret')
    def test_payment_signature_rejects_tampering(self):
        with self.assertRaises(ValidationError):
            billing.verify_signature('order_1', 'pay_1', 'forged')
        signature = hmac.new(b'test-secret', b'order_1|pay_1', hashlib.sha256).hexdigest()
        billing.verify_signature('order_1', 'pay_1', signature)

    @patch('saas.billing.provider')
    def test_payment_retry_extends_only_once(self, provider):
        order = BillingOrder.objects.create(tenant=self.ta, plan=self.plan, amount=10000, provider_order='order_one')
        provider.return_value = {'order_id': 'order_one', 'amount': 10000, 'currency': 'INR', 'status': 'captured'}
        billing.settle(order, 'pay_one')
        first = type(self.ta.subscription).objects.get(tenant=self.ta).expires_at
        billing.settle(order, 'pay_one')
        self.assertEqual(type(self.ta.subscription).objects.get(tenant=self.ta).expires_at, first)
        self.assertEqual(BillingOrder.objects.filter(tenant=self.ta, status='paid').count(), 1)

    @patch('saas.billing.provider')
    def test_wrong_payment_amount_does_not_activate(self, provider):
        order = BillingOrder.objects.create(tenant=self.ta, plan=self.plan, amount=10000, provider_order='order_one')
        provider.return_value = {'order_id': 'order_one', 'amount': 1, 'currency': 'INR', 'status': 'captured'}
        with self.assertRaises(ValidationError):
            billing.settle(order, 'pay_one')
        order.refresh_from_db()
        self.assertEqual(order.status, 'pending')

    @override_settings(RAZORPAY_WEBHOOK_SECRET='webhook-secret')
    def test_webhook_requires_signature(self):
        response = self.post('/billing/webhook/razorpay/', host='localhost')
        self.assertEqual(response.status_code, 400)

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from unittest.mock import Mock, patch

from django.core.exceptions import ValidationError
from django.db import connection, connections
from django.test import TransactionTestCase

from properties.models import Property
from . import billing
from .models import AuditEvent, BillingOrder, Membership
from .services import save_listing
from .tests import TwoBusinessFixture


@skipUnless(connection.vendor == 'mysql', 'Requires MySQL row locking')
class ConcurrentWriteTests(TwoBusinessFixture, TransactionTestCase):
    def race(self, operation):
        barrier = Barrier(2)

        def worker(index):
            connections.close_all()
            try:
                barrier.wait(timeout=10)
                return operation(index)
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(worker, range(2)))

    def test_quota_and_duplicate_payment_are_serialized(self):
        self.plan.listing_limit = 2  # One existing listing and one remaining slot.
        self.plan.save()
        membership = Membership.objects.get(tenant=self.ta, user=self.a)

        def create(index):
            obj = Property(tenant=self.ta, user=self.a, title=f'Concurrent {index}',
                           property_type=self.pa.property_type, state=self.state,
                           city=self.city, purpose='sale', price=100, area=100)
            form = Mock(instance=obj, files={})
            form.save.return_value = obj
            try:
                save_listing(form=form, tenant=self.ta, user=self.a, membership=membership)
                return 'saved'
            except ValidationError:
                return 'limited'

        self.assertCountEqual(self.race(create), ['saved', 'limited'])
        self.assertEqual(Property.objects.filter(tenant=self.ta).count(), 2)

        order = BillingOrder.objects.create(tenant=self.ta, plan=self.plan,
                                            amount=10000, provider_order='order_concurrent')
        payment = {'order_id': order.provider_order, 'amount': order.amount,
                   'currency': order.currency, 'status': 'captured'}
        with patch('saas.billing.provider', return_value=payment):
            self.race(lambda _: billing.settle(order, 'pay_concurrent'))
        order.refresh_from_db()
        self.assertEqual(order.status, 'paid')
        self.assertEqual(AuditEvent.objects.filter(tenant=self.ta, action='subscription.paid').count(), 1)

"""Razorpay adapter: never activate from browser-provided payment status."""
import hashlib
import hmac
import requests
from datetime import timedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from .models import AuditEvent, BillingOrder, Subscription, Tenant


def provider(method, path, data=None):
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise ValidationError('Online payments are not configured. Contact platform support.')
    try:
        response = requests.request(method, 'https://api.razorpay.com/v1/' + path,
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET), json=data, timeout=15)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        raise ValidationError('Payment provider is unavailable. Please retry shortly.') from exc


def create_order(tenant, plan):
    if not plan.is_active or plan.monthly_amount < 100:
        raise ValidationError('Online checkout for this plan is not enabled. Contact support.')
    order = BillingOrder.objects.create(tenant=tenant, plan=plan, amount=plan.monthly_amount)
    result = provider('POST', 'orders', {'amount': order.amount, 'currency': order.currency, 'receipt': str(order.uuid)})
    if not result.get('id') or result.get('amount') != order.amount or result.get('currency') != order.currency:
        raise ValidationError('Payment order could not be verified.')
    order.provider_order = result['id']
    order.save(update_fields=['provider_order'])
    return order


def verify_signature(order_id, payment_id, signature):
    if not settings.RAZORPAY_KEY_SECRET:
        raise ValidationError('Payments are not configured.')
    expected = hmac.new(settings.RAZORPAY_KEY_SECRET.encode(), f'{order_id}|{payment_id}'.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature or ''):
        raise ValidationError('Payment signature is invalid.')


def settle(order, payment_id):
    import re
    if not re.fullmatch(r'pay_[A-Za-z0-9]+', payment_id or ''):
        raise ValidationError('Payment ID is invalid.')
    payment = provider('GET', f'payments/{payment_id}')
    if payment.get('order_id') != order.provider_order or payment.get('amount') != order.amount or payment.get('currency') != order.currency or payment.get('status') != 'captured':
        raise ValidationError('Payment has not been captured for this order.')
    with transaction.atomic():
        order = BillingOrder.objects.select_for_update().get(pk=order.pk)
        if order.status == 'paid':
            if order.provider_payment != payment_id:
                raise ValidationError('This order has already been settled.')
            return order
        tenant = Tenant.objects.select_for_update().get(pk=order.tenant_id)
        if tenant.status == 'suspended':
            raise ValidationError('This business is suspended. Contact support to reconcile payment.')
        subscription = Subscription.objects.select_for_update().get(tenant=tenant)
        # A different plan starts now; same-plan paid renewals extend the paid period.
        start = timezone.now()
        if not subscription.is_trial and subscription.plan_id == order.plan_id:
            start = max(start, subscription.expires_at)
        subscription.plan = order.plan
        subscription.expires_at = start + timedelta(days=30)
        subscription.is_trial = False
        subscription.save()
        tenant.status = 'active'
        tenant.save(update_fields=['status'])
        order.status, order.provider_payment, order.paid_at = 'paid', payment_id, timezone.now()
        order.save(update_fields=['status', 'provider_payment', 'paid_at'])
        AuditEvent.objects.create(tenant=tenant, action='subscription.paid', detail=str(order.uuid))
    return order

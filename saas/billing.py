"""Razorpay adapter: never activate from browser-provided payment status."""
import json
import hashlib
import hmac
import requests
from datetime import timedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from .models import AuditEvent, BillingOrder, BillingSetting, PendingSignup, Subscription, Tenant, WebhookEvent


ZERO_UPGRADE_CREDIT = {
    'credit_amount': 0,
    'paid_amount': 0,
    'paid_taxable_amount': 0,
    'remaining_days': 0,
    'total_days': 0,
}


def _upgrade_credit(tenant, target_plan):
    if not tenant:
        return ZERO_UPGRADE_CREDIT.copy()
    try:
        subscription = Subscription.objects.select_related('plan').get(tenant=tenant)
    except Subscription.DoesNotExist:
        return ZERO_UPGRADE_CREDIT.copy()
    if subscription.is_trial or subscription.plan_id == target_plan.pk or subscription.expires_at <= timezone.now():
        return ZERO_UPGRADE_CREDIT.copy()
    paid_order = (
        BillingOrder.objects
        .filter(tenant=tenant, status='paid', plan_id=subscription.plan_id, paid_at__isnull=False)
        .order_by('-paid_at')
        .first()
    )
    if not paid_order or not paid_order.taxable_amount:
        return ZERO_UPGRADE_CREDIT.copy()
    total_days = max((subscription.expires_at.date() - paid_order.paid_at.date()).days, 1)
    remaining_days = max((subscription.expires_at.date() - timezone.now().date()).days, 0)
    return {
        'credit_amount': paid_order.amount,
        'paid_amount': paid_order.amount,
        'paid_taxable_amount': paid_order.taxable_amount,
        'remaining_days': remaining_days,
        'total_days': total_days,
    }


def duration_days(months):
    return max(1, int(months or 1)) * 30


def price_breakup(plan, tenant=None, months=1):
    settings_obj = BillingSetting.current()
    months = max(1, int(months or 1))
    subtotal = plan.monthly_amount * months
    plan_discount = subtotal * plan.discount_percent // 100
    taxable_before_credit = max(0, subtotal - plan_discount)
    credit_detail = _upgrade_credit(tenant, plan)
    credit = min(credit_detail['credit_amount'], taxable_before_credit)
    discount = plan_discount + credit
    taxable = max(0, subtotal - discount)
    gst = taxable * settings_obj.gst_percent // 100
    return {
        'subtotal_amount': subtotal,
        'discount_percent': plan.discount_percent,
        'discount_amount': discount,
        'plan_discount_amount': plan_discount,
        'upgrade_credit_amount': credit,
        'current_paid_amount': credit_detail['paid_amount'],
        'current_paid_taxable_amount': credit_detail['paid_taxable_amount'],
        'remaining_days': credit_detail['remaining_days'],
        'total_days': credit_detail['total_days'],
        'taxable_amount': taxable,
        'gst_percent': settings_obj.gst_percent,
        'gst_amount': gst,
        'amount': taxable + gst,
    }


def persisted_breakup(breakup):
    return {
        key: breakup[key]
        for key in (
            'subtotal_amount',
            'discount_percent',
            'discount_amount',
            'taxable_amount',
            'gst_percent',
            'gst_amount',
            'amount',
        )
    }


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


def create_order(tenant, plan, months=1):
    months = max(1, int(months or 1))
    breakup = price_breakup(plan, tenant=tenant, months=months)
    if not plan.is_active or breakup['amount'] < 100:
        raise ValidationError('Online checkout for this plan is not enabled. Contact support.')
    BillingOrder.objects.filter(tenant=tenant, status='pending').update(status='failed')
    order = BillingOrder.objects.create(tenant=tenant, plan=plan, billing_months=months, **persisted_breakup(breakup))
    result = provider('POST', 'orders', {
        'amount': order.amount,
        'currency': order.currency,
        'receipt': str(order.uuid),
        'payment_capture': 1,
        'notes': {
            'billing_order_uuid': str(order.uuid),
            'tenant_slug': tenant.slug,
            'tenant_id': str(tenant.pk),
            'plan_slug': plan.slug,
            'billing_months': str(months),
        },
    })
    if not result.get('id') or result.get('amount') != order.amount or result.get('currency') != order.currency:
        raise ValidationError('Payment order could not be verified.')
    order.provider_order = result['id']
    order.save(update_fields=['provider_order'])
    return order


def create_pending_signup_order(pending):
    if not pending.plan.is_active or pending.amount < 100:
        raise ValidationError('Online checkout for this plan is not enabled. Contact support.')
    result = provider('POST', 'orders', {
        'amount': pending.amount,
        'currency': pending.currency,
        'receipt': str(pending.uuid),
        'payment_capture': 1,
        'notes': {
            'pending_signup_uuid': str(pending.uuid),
            'username': pending.username,
            'plan_slug': pending.plan.slug,
            'billing_months': str(pending.billing_months),
        },
    })
    if not result.get('id') or result.get('amount') != pending.amount or result.get('currency') != pending.currency:
        raise ValidationError('Payment order could not be verified.')
    pending.provider_order = result['id']
    pending.save(update_fields=['provider_order'])
    return pending


def verify_signature(order_id, payment_id, signature):
    if not settings.RAZORPAY_KEY_SECRET:
        raise ValidationError('Payments are not configured.')
    expected = hmac.new(settings.RAZORPAY_KEY_SECRET.encode(), f'{order_id}|{payment_id}'.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature or ''):
        raise ValidationError('Payment signature is invalid.')


def verify_webhook_signature(body, signature):
    if not settings.RAZORPAY_WEBHOOK_SECRET:
        raise ValidationError('Webhook secret is not configured.')
    expected = hmac.new(settings.RAZORPAY_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature or ''):
        raise ValidationError('Webhook signature is invalid.')


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
        subscription.expires_at = start + timedelta(days=duration_days(order.billing_months))
        subscription.is_trial = False
        subscription.save()
        tenant.status = 'active'
        tenant.save(update_fields=['status'])
        order.status, order.provider_payment, order.paid_at = 'paid', payment_id, timezone.now()
        order.save(update_fields=['status', 'provider_payment', 'paid_at'])
        AuditEvent.objects.create(tenant=tenant, action='subscription.paid', detail=str(order.uuid))
        transaction.on_commit(lambda order_id=order.pk: _notify_payment_success(order_id))
    return order


def _entity(payload, name):
    return payload.get('payload', {}).get(name, {}).get('entity', {}) or {}


def _webhook_order_id(payload):
    payment = _entity(payload, 'payment')
    order = _entity(payload, 'order')
    return payment.get('order_id') or order.get('id') or ''


def _webhook_payment_id(payload):
    payment = _entity(payload, 'payment')
    return payment.get('id') or ''


@transaction.atomic
def mark_failed(order, payment_id=''):
    order = BillingOrder.objects.select_for_update().get(pk=order.pk)
    if order.status == 'paid':
        return order
    order.status = 'failed'
    if payment_id and not order.provider_payment:
        order.provider_payment = payment_id
    order.save(update_fields=['status', 'provider_payment'])
    AuditEvent.objects.create(tenant=order.tenant, action='subscription.payment_failed', detail=str(order.uuid))
    return order


@transaction.atomic
def mark_pending_failed(pending, payment_id=''):
    pending = PendingSignup.objects.select_for_update().get(pk=pending.pk)
    if pending.status == 'paid':
        return pending
    pending.status = 'failed'
    if payment_id and not pending.provider_payment:
        pending.provider_payment = payment_id
    pending.save(update_fields=['status', 'provider_payment'])
    return pending


def settle_pending_signup(pending, payment_id):
    import re
    if not re.fullmatch(r'pay_[A-Za-z0-9]+', payment_id or ''):
        raise ValidationError('Payment ID is invalid.')
    payment = provider('GET', f'payments/{payment_id}')
    if payment.get('order_id') != pending.provider_order or payment.get('amount') != pending.amount or payment.get('currency') != pending.currency or payment.get('status') != 'captured':
        raise ValidationError('Payment has not been captured for this order.')
    with transaction.atomic():
        pending = PendingSignup.objects.select_for_update().select_related('plan').get(pk=pending.pk)
        if pending.status == 'paid':
            raise ValidationError('This signup payment has already been used.')
        from django.contrib.auth import get_user_model
        from .services import provision
        User = get_user_model()
        if User.objects.filter(username__iexact=pending.username).exists():
            raise ValidationError('This username is no longer available.')
        user = User(
            username=pending.username,
            email=pending.email,
            phone=pending.phone,
            state=pending.state,
            country='India',
            user_type='owner',
        )
        if pending.password_hash:
            user.password = pending.password_hash
        else:
            user.set_unusable_password()
        user.save()
        tenant = provision(owner=user, name=pending.business_name, plan=pending.plan, slug=pending.username)
        subscription = Subscription.objects.select_for_update().get(tenant=tenant)
        subscription.is_trial = False
        subscription.expires_at = timezone.now() + timedelta(days=duration_days(pending.billing_months))
        subscription.save(update_fields=['is_trial', 'expires_at'])
        tenant.status = 'active'
        tenant.save(update_fields=['status'])
        order = BillingOrder.objects.create(
            tenant=tenant,
            plan=pending.plan,
            billing_months=pending.billing_months,
            amount=pending.amount,
            subtotal_amount=pending.subtotal_amount,
            discount_percent=pending.discount_percent,
            discount_amount=pending.discount_amount,
            taxable_amount=pending.taxable_amount,
            gst_percent=pending.gst_percent,
            gst_amount=pending.gst_amount,
            currency=pending.currency,
            provider_order=pending.provider_order,
            provider_payment=payment_id,
            status='paid',
            paid_at=timezone.now(),
        )
        pending.status = 'paid'
        pending.provider_payment = payment_id
        pending.paid_at = timezone.now()
        pending.save(update_fields=['status', 'provider_payment', 'paid_at'])
        AuditEvent.objects.create(tenant=tenant, actor=user, action='subscription.paid', detail=str(pending.uuid))
        transaction.on_commit(lambda order_id=order.pk: _notify_payment_success(order_id))
    return user, tenant


def _notify_payment_success(order_id):
    try:
        from .whatsapp import notify_payment_success
        order = BillingOrder.objects.select_related('tenant', 'tenant__owner', 'plan').get(pk=order_id)
        notify_payment_success(order=order)
    except Exception:
        import logging
        logging.getLogger(__name__).exception('WhatsApp payment success notification failed for order %s', order_id)


def process_webhook(body, signature, event_id=''):
    verify_webhook_signature(body, signature)
    try:
        payload = json.loads(body.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError('Webhook payload is invalid.') from exc
    event_id = event_id or payload.get('id')
    event_type = payload.get('event')
    if not event_id or not event_type:
        raise ValidationError('Webhook payload is missing event data.')
    event, created = WebhookEvent.objects.get_or_create(
        provider='razorpay',
        event_id=event_id,
        defaults={'event_type': event_type, 'payload': payload},
    )
    if not created:
        return event
    order_id = _webhook_order_id(payload)
    if order_id:
        order = BillingOrder.objects.filter(provider_order=order_id).select_related('tenant', 'plan').first()
        if order and event_type in ('payment.captured', 'order.paid'):
            settle(order, _webhook_payment_id(payload))
        elif order and event_type == 'payment.failed':
            mark_failed(order, _webhook_payment_id(payload))
        pending = PendingSignup.objects.filter(provider_order=order_id).select_related('plan').first()
        if pending and event_type in ('payment.captured', 'order.paid'):
            try:
                settle_pending_signup(pending, _webhook_payment_id(payload))
            except ValidationError:
                pass
        elif pending and event_type == 'payment.failed':
            mark_pending_failed(pending, _webhook_payment_id(payload))
    event.processed_at = timezone.now()
    event.save(update_fields=['processed_at', 'updated_at'])
    return event

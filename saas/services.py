from datetime import timedelta
import re
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from accounts.phone_utils import indian_whatsapp_number

from .models import AuditEvent, Domain, Membership, Plan, PlatformPurchaseAgreement, PurchaseAgreementAcceptance, Subscription, Tenant

RESERVED = {'www', 'admin', 'api', 'mail', 'app', 'saas', 'support', 'static', 'media', 'localhost', 'billing'}


def validate_slug(slug):
    slug = slug.strip().lower()
    if slug in RESERVED or not re.fullmatch(r'[a-z][a-z0-9-]{1,46}[a-z0-9]', slug):
        raise ValidationError('Use 3–48 lowercase letters, numbers or hyphens; start with a letter.')
    if Tenant.objects.filter(slug=slug).exists():
        raise ValidationError('This website address is already taken.')
    return slug


def allocate_business_slug(name, *, lock=False):
    from django.contrib.auth import get_user_model
    from django.utils.text import slugify

    from .models import PendingSignup

    if lock:
        # Serialize allocation without relying on a pre-submit availability check.
        Plan.objects.select_for_update().order_by('pk').first()
    base = slugify(name).replace('-', '')[:40]
    if len(base) < 3 or not base[0].isalpha() or base in RESERVED:
        base = 'business'
    slug = base
    index = 2
    root = settings.SAAS_CUSTOMER_DOMAIN_ROOT
    User = get_user_model()
    stale_before = timezone.now() - timedelta(minutes=30)
    PendingSignup.objects.filter(
        username__istartswith=base,
        status='pending',
        created_at__lt=stale_before,
    ).update(status='failed')
    while (
        Tenant.objects.filter(slug=slug).exists()
        or Domain.objects.filter(hostname=f'{slug}.{root}').exists()
        or User.objects.filter(username__iexact=slug).exists()
        or PendingSignup.objects.filter(username__iexact=slug, status='pending').exists()
    ):
        slug = f'{base}-{index}'
        index += 1
    return slug


@transaction.atomic
def provision(*, owner, name, plan, slug=None):
    # Unique slug + atomic transaction protects concurrent registrations and partial sites.
    if slug is None:
        slug = allocate_business_slug(name, lock=True)
    slug = validate_slug(slug)
    if not plan.is_active:
        raise ValidationError('This plan is unavailable.')
    from django.contrib.auth import get_user_model
    get_user_model().objects.select_for_update().get(pk=owner.pk)
    if Tenant.objects.filter(owner=owner).exists():
        raise ValidationError('A free workspace already exists for this account. Contact support for additional businesses.')
    tenant = Tenant.objects.create(owner=owner, name=name, slug=slug)
    Membership.objects.create(tenant=tenant, user=owner, role='owner', is_approved=True)
    trial_days = plan.trial_days if plan.trial_enabled else 0
    Subscription.objects.create(
        tenant=tenant,
        plan=plan,
        expires_at=timezone.now() + timedelta(days=trial_days),
        is_trial=plan.trial_enabled,
    )
    from core.models import SiteSetting
    from properties.models import PropertyType
    try:
        whatsapp = indian_whatsapp_number(owner.phone)
    except ValueError:
        whatsapp = re.sub(r'\D+', '', owner.phone or '')
    SiteSetting.objects.create(tenant=tenant, site_name=name, email=owner.email, phone=owner.phone, whatsapp=whatsapp, state=owner.state,
                               tagline='Find your next property', about_text=f'Welcome to {name}. Contact our team for property enquiries and site visits.')
    for title in ('Plot', 'Flat', 'Villa', 'Farm House', 'Commercial'):
        PropertyType.objects.create(tenant=tenant, name=title)
    AuditEvent.objects.create(tenant=tenant, actor=owner, action='workspace.created')
    if getattr(settings, 'SAAS_AUTO_DOMAINS', False):
        Domain.objects.create(tenant=tenant, hostname=f'{slug}.{settings.SAAS_CUSTOMER_DOMAIN_ROOT}',
                              is_platform=True, is_verified=True, provisioning_requested=True)
    return tenant


def subscription_for(tenant):
    try:
        subscription = Subscription.objects.select_related('plan', 'tenant').get(tenant=tenant)
    except Subscription.DoesNotExist:
        raise ValidationError('No subscription is configured. Contact support.')
    if not subscription.usable:
        raise ValidationError('Your subscription has expired. Renew from Business settings to continue editing.')
    return subscription


def active_purchase_agreement():
    return PlatformPurchaseAgreement.objects.filter(is_active=True).order_by('-updated_at', '-pk').first()


def record_purchase_agreement_acceptance(*, user=None, tenant=None, order=None, pending_signup=None, agreement=None, request=None):
    default_title = 'Plan Purchase Agreement'
    default_content = 'User confirmed the plan purchase terms before continuing to payment.'
    default_checkbox_label = 'I have read and agree to the plan purchase terms.'
    ip_address = None
    user_agent = ''
    if request is not None:
        forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
        ip_address = (forwarded_for.split(',', 1)[0] or request.META.get('REMOTE_ADDR') or '').strip() or None
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:1000]
    plan_name = ''
    amount = 0
    if order is not None:
        plan_name = order.plan.name
        amount = order.amount
        tenant = tenant or order.tenant
    elif pending_signup is not None:
        plan_name = pending_signup.plan.name
        amount = pending_signup.amount
    return PurchaseAgreementAcceptance.objects.create(
        user=user,
        tenant=tenant,
        order=order,
        pending_signup=pending_signup,
        agreement=agreement,
        agreement_title=agreement.title if agreement else default_title,
        agreement_content=agreement.content if agreement else default_content,
        checkbox_label=agreement.checkbox_label if agreement else default_checkbox_label,
        plan_name=plan_name,
        amount=amount,
        ip_address=ip_address,
        user_agent=user_agent,
        accepted_at=timezone.now(),
    )


@transaction.atomic
def save_listing(*, form, tenant, user, membership):
    Tenant.objects.select_for_update().get(pk=tenant.pk)
    membership = Membership.objects.filter(tenant=tenant, user=user, is_active=True).first()
    if not membership or not membership.can_list:
        raise PermissionDenied('Only approved business members can manage listings.')
    if form.instance.pk:
        from properties.models import Property
        original = Property.objects.get(pk=form.instance.pk)
        if original.tenant_id != tenant.pk or (not membership.can_manage and original.user_id != user.pk):
            raise PermissionDenied('This listing is not available to your account.')
    subscription = subscription_for(tenant)
    from properties.models import Property
    if not form.instance.pk and Property.objects.filter(tenant=tenant).count() >= subscription.plan.listing_limit:
        raise ValidationError('Your listing limit has been reached. Delete a listing or upgrade your plan.')
    from .uploads import ensure_storage
    ensure_storage(tenant, sum(f.size for f in form.files.values()))
    obj = form.save(commit=False)
    obj.tenant = tenant
    if not obj.pk:
        obj.user = user
        obj.is_active = membership.can_manage
        obj.is_verified = False
    elif not membership.can_manage:
        obj.is_active = False
    obj.save()
    form.save_m2m()
    AuditEvent.objects.create(tenant=tenant, actor=user, action='listing.saved', detail=str(obj.pk))
    return obj


def validate_domain_for_tenant(hostname):
    from .models import normalize_domain
    hostname = normalize_domain(hostname)
    base = settings.SAAS_CUSTOMER_DOMAIN_ROOT
    if hostname == base or hostname.endswith('.' + base) or hostname.endswith(('.localhost', '.local', '.internal')):
        raise ValidationError('Use a public custom domain outside the platform domain.')
    import ipaddress
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        return hostname
    raise ValidationError('IP addresses cannot be used as custom domains.')


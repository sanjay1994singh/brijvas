import secrets
import uuid
from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, RegexValidator
from django.db import models
from django.utils import timezone


def domain_token():
    return secrets.token_urlsafe(32)


def normalize_domain(value):
    value = str(value).strip().lower().rstrip('.')
    if any(c in value for c in '/:@?#*') or len(value) > 253:
        raise ValidationError('Enter a hostname only, without scheme, path or port.')
    labels = value.split('.')
    if len(labels) < 2 or any(not label or len(label) > 63 for label in labels):
        raise ValidationError('Enter a valid domain name.')
    import re
    if not all(re.fullmatch(r'[a-z0-9](?:[a-z0-9-]*[a-z0-9])?', label) for label in labels):
        raise ValidationError('Enter a valid ASCII domain name.')
    return value


class Plan(models.Model):
    name = models.CharField(max_length=80)
    slug = models.SlugField(unique=True)
    monthly_amount = models.PositiveIntegerField(default=0, help_text='Minor units (paise). Zero disables online checkout.')
    discount_percent = models.PositiveIntegerField(default=0, validators=[MaxValueValidator(100)], help_text='Percentage discount applied at checkout.')
    listing_limit = models.PositiveIntegerField(default=50)
    staff_limit = models.PositiveIntegerField(default=3)
    storage_mb = models.PositiveIntegerField(default=1024)
    custom_domain = models.BooleanField(default=False)
    trial_enabled = models.BooleanField(default=True)
    trial_days = models.PositiveIntegerField(default=7)
    is_active = models.BooleanField(default=True)

    @property
    def price(self):
        return self.monthly_amount / 100

    @property
    def discounted_amount(self):
        if not self.monthly_amount:
            return 0
        return max(0, self.monthly_amount - (self.monthly_amount * self.discount_percent // 100))

    @property
    def discounted_price(self):
        return self.discounted_amount / 100

    @property
    def has_discount(self):
        return bool(self.discount_percent and self.discounted_amount < self.monthly_amount)

    def __str__(self):
        return self.name

    @property
    def active_features(self):
        configured = [feature.text for feature in self.features.filter(is_active=True).order_by('sort_order', 'id')]
        if configured:
            return configured
        return [
            f'{self.listing_limit} property listings',
            f'{self.staff_limit} staff seats',
            'Custom domain support',
        ]


class PlanFeature(models.Model):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='features')
    text = models.CharField(max_length=160)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['sort_order', 'id']

    def __str__(self):
        return self.text


class BillingSetting(models.Model):
    gst_percent = models.PositiveIntegerField(default=18, validators=[MaxValueValidator(100)])
    business_name = models.CharField(max_length=160, default='SHRI INFOWAVE PRIVATE LIMITED')
    business_address = models.TextField(default='101 Govind Kund Tila, Radha Niwas, Vrindaban, Mathura, Uttar Pradesh, India')
    gstin = models.CharField(max_length=32, default='09ABUCS7544P1Z2', blank=True)
    pan = models.CharField(max_length=20, default='ABUCS7544P', blank=True)
    cin = models.CharField(max_length=32, default='U62012UW2026PTC257361', blank=True)
    support_email = models.EmailField(default='shriinfowaveprivatelimited@gmail.com', blank=True)
    whatsapp_number = models.CharField(max_length=20, default='918279408396', blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Billing setting'
        verbose_name_plural = 'Billing settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def current(cls):
        return cls.objects.get_or_create(pk=1, defaults={'gst_percent': 18})[0]

    def __str__(self):
        return 'Billing settings'


class Tenant(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=160)
    slug = models.SlugField(unique=True, max_length=48, validators=[RegexValidator(r'^[a-z][a-z0-9-]*$')])
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='businesses', null=True, blank=True)
    status = models.CharField(max_length=16, choices=[('trial', 'Trial'), ('active', 'Active'), ('suspended', 'Suspended')], default='trial')
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def public_url(self):
        domain = self.domains.filter(is_primary=True, is_verified=True, ssl_ready=True).first()
        if domain:
            return f'https://{domain.hostname}'
        if settings.SAAS_USE_PATH_URLS:
            if self.slug == settings.SAAS_ROOT_TENANT:
                return settings.SAAS_BASE_URL
            return f'{settings.SAAS_BASE_URL}/sites/{self.slug}'
        base = urlsplit(settings.SAAS_BASE_URL)
        return f'{base.scheme}://{self.slug}.{settings.SAAS_CUSTOMER_DOMAIN_ROOT}'

    def __str__(self):
        return self.name


class Membership(models.Model):
    ROLES = [('owner', 'Business owner'), ('admin', 'Business admin'), ('agent', 'Agent'), ('seller', 'Seller'), ('buyer', 'Buyer')]
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=12, choices=ROLES, default='buyer')
    is_active = models.BooleanField(default=True)
    is_approved = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['tenant', 'user'], name='saas_unique_membership')]

    @property
    def can_manage(self):
        return self.is_active and self.is_approved and self.role in ('owner', 'admin')

    @property
    def can_list(self):
        return self.is_active and self.is_approved and self.role in ('owner', 'admin', 'seller', 'agent')


class Subscription(models.Model):
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    expires_at = models.DateTimeField()
    is_trial = models.BooleanField(default=True)

    @property
    def usable(self):
        return self.tenant.status != 'suspended' and self.expires_at > timezone.now()


class Domain(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='domains')
    hostname = models.CharField(max_length=253, unique=True, validators=[normalize_domain])
    token = models.CharField(max_length=64, default=domain_token, editable=False)
    is_verified = models.BooleanField(default=False)
    ssl_ready = models.BooleanField(default=False)
    is_primary = models.BooleanField(default=False)
    error = models.CharField(max_length=300, blank=True)
    is_platform = models.BooleanField(default=False)
    provisioning_requested = models.BooleanField(default=False)
    last_attempt_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        self.hostname = normalize_domain(self.hostname)
        super().save(*args, **kwargs)

    @property
    def txt_name(self):
        return f'_vistaflo-site.{self.hostname}'

    @property
    def txt_value(self):
        return f'vistaflo-site-verification={self.token}'


class BillingOrder(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, related_name='orders')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    billing_months = models.PositiveSmallIntegerField(default=1)
    amount = models.PositiveIntegerField()
    subtotal_amount = models.PositiveIntegerField(default=0)
    discount_percent = models.PositiveIntegerField(default=0)
    discount_amount = models.PositiveIntegerField(default=0)
    taxable_amount = models.PositiveIntegerField(default=0)
    gst_percent = models.PositiveIntegerField(default=18)
    gst_amount = models.PositiveIntegerField(default=0)
    currency = models.CharField(max_length=3, default='INR')
    provider_order = models.CharField(max_length=100, unique=True, null=True, blank=True)
    provider_payment = models.CharField(max_length=100, unique=True, null=True, blank=True)
    status = models.CharField(max_length=12, default='pending', choices=[('pending', 'Pending'), ('paid', 'Paid'), ('failed', 'Failed')])
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    @property
    def amount_rupees(self):
        return self.amount / 100

    @property
    def subtotal_rupees(self):
        return self.subtotal_amount / 100

    @property
    def discount_rupees(self):
        return self.discount_amount / 100

    @property
    def taxable_rupees(self):
        return self.taxable_amount / 100

    @property
    def gst_rupees(self):
        return self.gst_amount / 100


class WebhookEvent(models.Model):
    provider = models.CharField(max_length=40, default='razorpay')
    event_id = models.CharField(max_length=120)
    event_type = models.CharField(max_length=120)
    payload = models.JSONField(default=dict)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['provider', 'event_id'], name='saas_unique_provider_webhook_event'),
        ]


class PlatformPurchaseAgreement(models.Model):
    title = models.CharField(max_length=180, default='Plan Purchase Agreement')
    content = models.TextField()
    checkbox_label = models.CharField(
        max_length=255,
        default='I have read and agree to the plan purchase terms.',
    )
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_active', '-updated_at']

    def __str__(self):
        return self.title


class PendingSignup(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    business_name = models.CharField(max_length=160)
    username = models.CharField(max_length=150)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20)
    state = models.CharField(max_length=100, blank=True)
    password_hash = models.CharField(max_length=128, blank=True)
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    billing_months = models.PositiveSmallIntegerField(default=1)
    amount = models.PositiveIntegerField()
    subtotal_amount = models.PositiveIntegerField(default=0)
    discount_percent = models.PositiveIntegerField(default=0)
    discount_amount = models.PositiveIntegerField(default=0)
    taxable_amount = models.PositiveIntegerField(default=0)
    gst_percent = models.PositiveIntegerField(default=18)
    gst_amount = models.PositiveIntegerField(default=0)
    currency = models.CharField(max_length=3, default='INR')
    provider_order = models.CharField(max_length=100, unique=True, null=True, blank=True)
    provider_payment = models.CharField(max_length=100, unique=True, null=True, blank=True)
    status = models.CharField(max_length=16, default='pending', choices=[('pending', 'Pending'), ('paid', 'Paid'), ('failed', 'Failed')])
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    @property
    def amount_rupees(self):
        return self.amount / 100

    @property
    def subtotal_rupees(self):
        return self.subtotal_amount / 100

    @property
    def discount_rupees(self):
        return self.discount_amount / 100

    @property
    def taxable_rupees(self):
        return self.taxable_amount / 100

    @property
    def gst_rupees(self):
        return self.gst_amount / 100


class PurchaseAgreementAcceptance(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='vistaflo_purchase_agreement_acceptances', null=True, blank=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='purchase_agreement_acceptances', null=True, blank=True)
    order = models.ForeignKey(BillingOrder, on_delete=models.CASCADE, related_name='purchase_agreement_acceptances', null=True, blank=True)
    pending_signup = models.ForeignKey(PendingSignup, on_delete=models.CASCADE, related_name='purchase_agreement_acceptances', null=True, blank=True)
    agreement = models.ForeignKey(PlatformPurchaseAgreement, on_delete=models.SET_NULL, null=True, blank=True, related_name='acceptances')
    agreement_title = models.CharField(max_length=180)
    agreement_content = models.TextField()
    checkbox_label = models.CharField(max_length=255)
    plan_name = models.CharField(max_length=120, blank=True)
    amount = models.PositiveIntegerField(default=0)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    accepted_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-accepted_at', '-created_at']
        indexes = [
            models.Index(fields=['user', 'accepted_at']),
            models.Index(fields=['tenant', 'accepted_at']),
            models.Index(fields=['order', 'accepted_at']),
            models.Index(fields=['pending_signup', 'accepted_at']),
        ]

    @property
    def amount_rupees(self):
        return self.amount / 100

    def __str__(self):
        name = self.user or self.tenant or self.pending_signup or 'Customer'
        return f'{name} accepted {self.agreement_title}'


class AuditEvent(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='events')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=80)
    detail = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class TenantOwnedModel(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    allow_global_tenant = False

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.tenant_id and not self.allow_global_tenant:
            raise ValidationError('A business workspace is required.')
        for field in ('user', 'author'):
            if hasattr(self, f'{field}_id') and getattr(self, f'{field}_id'):
                if not Membership.objects.filter(tenant_id=self.tenant_id, user_id=getattr(self, f'{field}_id')).exists():
                    raise ValidationError('The selected account does not belong to this business.')
        for field in ('property_type', 'category'):
            if hasattr(self, f'{field}_id') and getattr(self, f'{field}_id'):
                related_tenant_id = getattr(self, field).tenant_id
                if related_tenant_id and related_tenant_id != self.tenant_id:
                    raise ValidationError('Related record belongs to a different workspace.')
        if self.pk:
            old_tenant = type(self).objects.filter(pk=self.pk).values_list('tenant_id', flat=True).first()
            if old_tenant and old_tenant != self.tenant_id:
                raise ValidationError('Moving records between businesses is not supported.')
        super().save(*args, **kwargs)


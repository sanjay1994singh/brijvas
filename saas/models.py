import secrets
import uuid
from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
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
    listing_limit = models.PositiveIntegerField(default=50)
    staff_limit = models.PositiveIntegerField(default=3)
    storage_mb = models.PositiveIntegerField(default=1024)
    custom_domain = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    @property
    def price(self):
        return self.monthly_amount / 100

    def __str__(self):
        return self.name


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
        return f'_property-saas.{self.hostname}'

    @property
    def txt_value(self):
        return f'property-saas-verification={self.token}'


class BillingOrder(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, related_name='orders')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    amount = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default='INR')
    provider_order = models.CharField(max_length=100, unique=True, null=True, blank=True)
    provider_payment = models.CharField(max_length=100, unique=True, null=True, blank=True)
    status = models.CharField(max_length=12, default='pending', choices=[('pending', 'Pending'), ('paid', 'Paid')])
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)


class AuditEvent(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='events')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=80)
    detail = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class TenantOwnedModel(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.tenant_id:
            raise ValidationError('A business workspace is required.')
        for field in ('user', 'author'):
            if hasattr(self, f'{field}_id') and getattr(self, f'{field}_id'):
                if not Membership.objects.filter(tenant_id=self.tenant_id, user_id=getattr(self, f'{field}_id')).exists():
                    raise ValidationError('The selected account does not belong to this business.')
        for field in ('property_type', 'category'):
            if hasattr(self, f'{field}_id') and getattr(self, f'{field}_id'):
                if getattr(self, field).tenant_id != self.tenant_id:
                    raise ValidationError('Related record belongs to a different workspace.')
        if self.pk:
            old_tenant = type(self).objects.filter(pk=self.pk).values_list('tenant_id', flat=True).first()
            if old_tenant and old_tenant != self.tenant_id:
                raise ValidationError('Moving records between businesses is not supported.')
        super().save(*args, **kwargs)


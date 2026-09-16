from django.contrib import admin
from .models import AuditEvent, BillingOrder, BillingSetting, Domain, Membership, PendingSignup, Plan, PlanFeature, PlatformPurchaseAgreement, PurchaseAgreementAcceptance, Subscription, Tenant, WebhookEvent


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'status', 'owner', 'created_at')
    search_fields = ('name', 'slug')
    readonly_fields = ('uuid',)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ('hostname', 'tenant', 'is_verified', 'ssl_ready', 'is_primary')
    readonly_fields = ('token', 'is_verified', 'ssl_ready', 'is_primary', 'is_platform', 'provisioning_requested', 'last_attempt_at', 'error')

    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields + (('hostname', 'tenant') if obj else ())


@admin.register(AuditEvent, PendingSignup, WebhookEvent)
class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(BillingOrder)
class BillingOrderAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'tenant', 'plan', 'status', 'amount_rupees', 'gst_percent', 'provider_order', 'provider_payment', 'created_at', 'paid_at')
    list_filter = ('status', 'plan', 'gst_percent', 'created_at', 'paid_at')
    search_fields = ('uuid', 'tenant__name', 'tenant__slug', 'provider_order', 'provider_payment')
    readonly_fields = ('uuid', 'tenant', 'plan', 'amount', 'subtotal_amount', 'discount_percent', 'discount_amount', 'taxable_amount', 'gst_percent', 'gst_amount', 'currency', 'provider_order', 'provider_payment', 'status', 'created_at', 'paid_at')
    fields = readonly_fields

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(BillingSetting)
class BillingSettingAdmin(admin.ModelAdmin):
    fields = ('gst_percent', 'business_name', 'gstin', 'pan', 'cin', 'support_email', 'whatsapp_number', 'business_address')

    def has_add_permission(self, request):
        return not BillingSetting.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PlatformPurchaseAgreement)
class PlatformPurchaseAgreementAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'updated_at')
    list_filter = ('is_active', 'updated_at')
    search_fields = ('title', 'content', 'checkbox_label')
    fields = ('title', 'content', 'checkbox_label', 'is_active')


@admin.register(PurchaseAgreementAcceptance)
class PurchaseAgreementAcceptanceAdmin(admin.ModelAdmin):
    list_display = ('agreement_title', 'user', 'tenant', 'plan_name', 'amount_rupees', 'accepted_at')
    list_filter = ('agreement', 'plan_name', 'accepted_at')
    search_fields = ('agreement_title', 'agreement_content', 'checkbox_label', 'user__username', 'user__phone', 'tenant__name', 'tenant__slug', 'plan_name')
    readonly_fields = ('user', 'tenant', 'order', 'pending_signup', 'agreement', 'agreement_title', 'agreement_content', 'checkbox_label', 'plan_name', 'amount', 'ip_address', 'user_agent', 'accepted_at', 'created_at')
    fields = readonly_fields

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    class FeatureInline(admin.TabularInline):
        model = PlanFeature
        extra = 1
        fields = ('text', 'sort_order', 'is_active')

    list_display = ('name', 'slug', 'price', 'discount_percent', 'discounted_price', 'listing_limit', 'staff_limit', 'custom_domain', 'trial_enabled', 'trial_days', 'is_active')
    list_editable = ('discount_percent', 'listing_limit', 'staff_limit', 'custom_domain', 'trial_enabled', 'trial_days', 'is_active')
    fields = ('name', 'slug', 'monthly_amount', 'discount_percent', 'listing_limit', 'staff_limit', 'custom_domain', 'trial_enabled', 'trial_days', 'is_active')
    inlines = (FeatureInline,)
    prepopulated_fields = {'slug': ('name',)}

admin.site.register(Subscription)
admin.site.register(Membership)

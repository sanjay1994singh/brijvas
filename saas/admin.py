from django.contrib import admin
from .models import AuditEvent, BillingOrder, Domain, Membership, Plan, Subscription, Tenant


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


@admin.register(AuditEvent, BillingOrder)
class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(Plan)
admin.site.register(Subscription)
admin.site.register(Membership)

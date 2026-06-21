from django.contrib import admin

from .models import (
    Property,
    PropertyGallery,
    PropertyType,
    Amenity,
    Wishlist,
    CompareProperty,
    PropertyReview,
    PropertyView,
)

class PropertyGalleryInline(
    admin.TabularInline
):
    model = PropertyGallery
    extra = 1


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "city",
        "price",
        "is_featured",
        "is_active",
    )

    list_filter = (
        "city",
        "property_type",
        "is_featured",
    )

    search_fields = (
        "title",
        "description",
    )

    readonly_fields = (
        "slug",
    )

    inlines = [
        PropertyGalleryInline
    ]


@admin.register(PropertyType)
class PropertyTypeAdmin(admin.ModelAdmin):
    readonly_fields = (
        "slug",
    )

    list_display = (
        "name",
        "slug",
    )

    search_fields = (
        "name",
    )


admin.site.register(Amenity)
admin.site.register(Wishlist)
admin.site.register(CompareProperty)
admin.site.register(PropertyReview)


@admin.register(PropertyView)
class PropertyViewAdmin(admin.ModelAdmin):
    list_display = (
        "property",
        "user",
        "ip_address",
        "created_at",
    )

    list_filter = (
        "created_at",
    )

    search_fields = (
        "property__title",
        "session_key",
        "ip_address",
    )

    readonly_fields = (
        "property",
        "user",
        "session_key",
        "ip_address",
        "user_agent_hash",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

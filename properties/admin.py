from django.contrib import admin

from .models import (
    Property,
    PropertyGallery,
    PropertyType,
    Amenity,
    Wishlist,
    CompareProperty,
    PropertyReview,
)

from .models import (
    Wishlist,
    CompareProperty,
    PropertyReview
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

    prepopulated_fields = {
        "slug": ("title",)
    }

    inlines = [
        PropertyGalleryInline
    ]


admin.site.register(PropertyType)
admin.site.register(Amenity)
admin.site.register(Wishlist)
admin.site.register(CompareProperty)
admin.site.register(PropertyReview)

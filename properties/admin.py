from django.contrib import admin
from .models import (
    Wishlist,
    CompareProperty,
    PropertyReview
)

admin.site.register(Wishlist)
admin.site.register(CompareProperty)
admin.site.register(PropertyReview)

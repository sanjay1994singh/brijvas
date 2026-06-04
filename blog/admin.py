from django.contrib import admin
from .models import (
    Blog,
    BlogCategory,
    BlogComment
)

admin.site.register(BlogCategory)
admin.site.register(BlogComment)


@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    prepopulated_fields = {
        "slug": ("title",)
    }

    list_display = (
        "title",
        "category",
        "author",
        "is_published",
        "created_at"
    )

    list_filter = (
        "category",
        "is_published"
    )

    search_fields = (
        "title",
        "content"
    )

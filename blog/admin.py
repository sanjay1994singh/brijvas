from django.contrib import admin
from .models import (
    Blog,
    BlogCategory,
    BlogComment
)

@admin.register(BlogCategory)
class BlogCategoryAdmin(admin.ModelAdmin):
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


admin.site.register(BlogComment)


@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    readonly_fields = (
        "slug",
    )

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

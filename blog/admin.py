from django.contrib import admin
from .models import (
    Blog,
    BlogCategory,
    BlogComment,
    BlogView
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


@admin.register(BlogView)
class BlogViewAdmin(admin.ModelAdmin):
    list_display = (
        "blog",
        "user",
        "ip_address",
        "created_at",
    )

    list_filter = (
        "created_at",
    )

    search_fields = (
        "blog__title",
        "session_key",
        "ip_address",
    )

    readonly_fields = (
        "blog",
        "user",
        "session_key",
        "ip_address",
        "user_agent_hash",
        "visitor_key",
        "created_at",
    )

    def has_add_permission(self, request):
        return False


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

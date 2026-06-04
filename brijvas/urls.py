from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from django.contrib.sitemaps.views import sitemap
from properties.sitemap import PropertySitemap
from blog.sitemap import BlogSitemap

sitemaps = {
    "properties": PropertySitemap,
    "blogs": BlogSitemap,
}

urlpatterns = [
    path("admin/", admin.site.urls),

    path("", include("core.urls")),

    path("accounts/", include("accounts.urls")),

    path("properties/", include("properties.urls")),

    path("dashboard/", include("dashboard.urls")),

    path("blog/", include("blog.urls")),

    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="sitemap",
    ),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )

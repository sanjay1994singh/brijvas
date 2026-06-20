from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from django.contrib.sitemaps.views import sitemap
from properties.sitemap import PropertySitemap, PropertyTypeSitemap
from blog.sitemap import BlogSitemap, BlogCategorySitemap
from core.sitemaps import StaticViewSitemap
from core import views

sitemaps = {
    'static': StaticViewSitemap,
    "properties": PropertySitemap,
    "property_types": PropertyTypeSitemap,
    "blogs": BlogSitemap,
    "blog_categories": BlogCategorySitemap,
}

urlpatterns = [
    path("admin/", admin.site.urls),
    path('auth/', include('social_django.urls', namespace='social')),

    path(
        "google90e7d13ae9f2d42d.html",
        views.google_verify,
        name="google_verify"
    ),

    path("", include("core.urls")),

    path("accounts/", include("accounts.urls")),

    path("properties/", include("properties.urls")),

    path("dashboard/", include("dashboard.urls")),

    path("blog/", include("blog.urls")),

    path(
        'sitemap.xml',
        sitemap,
        {'sitemaps': sitemaps},
        name='django.contrib.sitemaps.views.sitemap'
    ),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )

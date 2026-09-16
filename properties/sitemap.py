from saas.scoping import scoped
from django.contrib.sitemaps import Sitemap
from .models import Property, PropertyType


class PropertySitemap(Sitemap):
    def __init__(self, tenant):
        self.tenant = tenant

    changefreq = "daily"

    priority = 0.9

    def items(self):
        return scoped(Property, self.tenant).filter(
            is_active=True
        )

    def lastmod(self, obj):
        return obj.updated_at


class PropertyTypeSitemap(Sitemap):
    def __init__(self, tenant):
        self.tenant = tenant

    changefreq = "weekly"

    priority = 0.7

    def items(self):
        return PropertyType.objects.filter(tenant__isnull=True).order_by("name")

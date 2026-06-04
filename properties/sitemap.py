from django.contrib.sitemaps import Sitemap
from .models import Property


class PropertySitemap(Sitemap):
    changefreq = "daily"

    priority = 0.9

    def items(self):
        return Property.objects.filter(
            is_active=True
        )

    def lastmod(self, obj):
        return obj.updated_at

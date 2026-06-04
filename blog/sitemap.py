from django.contrib.sitemaps import Sitemap
from .models import Blog


class BlogSitemap(Sitemap):
    changefreq = "weekly"

    priority = 0.8

    def items(self):
        return Blog.objects.all()

    def lastmod(self, obj):
        return obj.created_at

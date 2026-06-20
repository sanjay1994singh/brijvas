from django.contrib.sitemaps import Sitemap
from .models import Blog, BlogCategory


class BlogSitemap(Sitemap):
    changefreq = "weekly"

    priority = 0.8

    def items(self):
        return Blog.objects.filter(
            is_published=True
        )

    def lastmod(self, obj):
        return obj.updated_at


class BlogCategorySitemap(Sitemap):
    changefreq = "weekly"

    priority = 0.6

    def items(self):
        return BlogCategory.objects.all()

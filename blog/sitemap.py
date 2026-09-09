from saas.scoping import scoped
from django.contrib.sitemaps import Sitemap
from .models import Blog, BlogCategory


class BlogSitemap(Sitemap):
    def __init__(self, tenant):
        self.tenant = tenant

    changefreq = "weekly"

    priority = 0.8

    def items(self):
        return scoped(Blog, self.tenant).filter(
            is_published=True
        )

    def lastmod(self, obj):
        return obj.updated_at


class BlogCategorySitemap(Sitemap):
    def __init__(self, tenant):
        self.tenant = tenant

    changefreq = "weekly"

    priority = 0.6

    def items(self):
        return scoped(BlogCategory, self.tenant).all()

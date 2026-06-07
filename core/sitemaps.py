from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    priority = 0.7

    changefreq = "monthly"

    def items(self):
        return [

            'home',

            'about',

            'contact',

            'blog_list',

            'property_list',

        ]

    def location(self, item):
        return reverse(item)

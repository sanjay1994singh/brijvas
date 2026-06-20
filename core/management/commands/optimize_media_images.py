from django.core.management.base import BaseCommand

from blog.models import Blog
from core.images import optimize_uploaded_image
from properties.models import Property, PropertyGallery, PropertyType


class Command(BaseCommand):
    help = "Compress existing uploaded property and blog images."

    def handle(self, *args, **options):
        optimized = 0

        for property_type in PropertyType.objects.exclude(image=""):
            optimize_uploaded_image(
                property_type.image,
                max_size=(700, 500),
                target_kb=180
            )
            optimized += 1

        for property_obj in Property.objects.exclude(featured_image=""):
            optimize_uploaded_image(
                property_obj.featured_image,
                max_size=(1600, 1200),
                target_kb=450
            )
            optimized += 1

        for gallery_image in PropertyGallery.objects.exclude(image=""):
            optimize_uploaded_image(
                gallery_image.image,
                max_size=(1600, 1200),
                target_kb=450
            )
            optimized += 1

        for post in Blog.objects.exclude(featured_image=""):
            optimize_uploaded_image(
                post.featured_image,
                max_size=(1400, 900),
                target_kb=380
            )
            optimized += 1

        self.stdout.write(
            self.style.SUCCESS(f"Optimized {optimized} uploaded images.")
        )

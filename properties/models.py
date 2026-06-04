from django.db import models
from django.utils.text import slugify

from accounts.models import User
from locations.models import State, City


class PropertyType(models.Model):
    name = models.CharField(max_length=100)

    slug = models.SlugField(unique=True)

    icon = models.CharField(max_length=100, blank=True)

    image = models.ImageField(
        upload_to='property-types/'
    )

    def __str__(self):
        return self.name

# Example Data
# Plot
# Villa
# Flat
# Farm House
# Agriculture Land
# Hotel
# Commercial Shop
# Office
# Warehouse

class Property(models.Model):
    PURPOSE_CHOICES = (
        ('sale', 'Sale'),
        ('resale', 'Resale'),
        ('rent', 'Rent'),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='properties'
    )

    property_type = models.ForeignKey(
        PropertyType,
        on_delete=models.CASCADE
    )

    title = models.CharField(max_length=255)

    slug = models.SlugField(
        unique=True,
        blank=True
    )

    purpose = models.CharField(
        max_length=20,
        choices=PURPOSE_CHOICES
    )

    state = models.ForeignKey(
        State,
        on_delete=models.CASCADE
    )

    city = models.ForeignKey(
        City,
        on_delete=models.CASCADE
    )

    address = models.TextField()

    description = models.TextField()

    price = models.DecimalField(
        max_digits=15,
        decimal_places=2
    )

    area = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    area_unit = models.CharField(
        max_length=20,
        default='sqft'
    )

    bedrooms = models.PositiveIntegerField(
        default=0
    )

    bathrooms = models.PositiveIntegerField(
        default=0
    )

    parking = models.PositiveIntegerField(
        default=0
    )

    furnishing = models.CharField(
        max_length=100,
        blank=True
    )

    featured_image = models.ImageField(
        upload_to='properties/'
    )

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True
    )

    is_featured = models.BooleanField(
        default=False
    )

    is_verified = models.BooleanField(
        default=False
    )

    is_active = models.BooleanField(
        default=True
    )

    views = models.PositiveIntegerField(
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class PropertyGallery(models.Model):
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='gallery'
    )

    image = models.ImageField(
        upload_to='property-gallery/'
    )

    def __str__(self):
        return self.property.title


class Amenity(models.Model):
    name = models.CharField(max_length=100)

    icon = models.CharField(
        max_length=100,
        blank=True
    )

    def __str__(self):
        return self.name

# Examples:
#
# Swimming Pool
# Garden
# Security
# Lift
# Gym
# Club House
# Parking

class PropertyAmenity(models.Model):
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE
    )

    amenity = models.ForeignKey(
        Amenity,
        on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ('property', 'amenity')


class PropertyVideo(models.Model):
    property = models.OneToOneField(
        Property,
        on_delete=models.CASCADE
    )

    youtube_url = models.URLField()

    def __str__(self):
        return self.property.title

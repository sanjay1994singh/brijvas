from django.db import models
from django.urls import reverse
from accounts.models import User
from locations.models import State, City
from django.conf import settings
from django_ckeditor_5.fields import CKEditor5Field
from core.images import optimize_uploaded_image
from core.seo import unique_slug
from decimal import Decimal, ROUND_HALF_UP


class PropertyType(models.Model):
    name = models.CharField(max_length=100)

    slug = models.SlugField(
        unique=True,
        blank=True
    )

    icon = models.CharField(max_length=100, blank=True)

    image = models.ImageField(
        upload_to='property-types/'
    )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(
                self,
                self.name,
                fallback="property-type"
            )

        super().save(*args, **kwargs)
        optimize_uploaded_image(
            self.image,
            max_size=(700, 500),
            target_kb=180
        )

    def get_absolute_url(self):
        return reverse(
            "category_properties",
            kwargs={"slug": self.slug}
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

    AREA_UNIT_CHOICES = (
        ('sqft', 'Sqft'),
        ('gaj', 'Gaj'),
    )

    SQFT_PER_GAJ = Decimal("9")

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='properties'
    )

    property_type = models.ForeignKey(
        PropertyType,
        on_delete=models.CASCADE
    )

    title = models.CharField(
        max_length=255,
        blank=True
    )

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

    address = models.TextField(
        blank=True
    )

    description = CKEditor5Field(
        config_name="extends",
        blank=True
    )

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
        choices=AREA_UNIT_CHOICES,
        default='sqft'
    )

    area_sqft = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        editable=False
    )

    area_gaj = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        editable=False
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

    def _rounded_area(self, value):
        return Decimal(value).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

    def _clean_decimal_display(self, value):
        if value is None:
            return ""

        normalized = Decimal(value).normalize()
        return format(normalized, "f")

    def _area_for_title(self):
        area_value = self.area_gaj if self.area_unit == "gaj" else self.area_sqft
        unit = "Gaj" if self.area_unit == "gaj" else "Sqft"

        if area_value:
            return f"{self._clean_decimal_display(area_value)} {unit}"

        return ""

    @property
    def display_area_sqft(self):
        if self.area_sqft is not None:
            return self.area_sqft

        if self.area is None:
            return None

        if self.area_unit == "gaj":
            return self._rounded_area(
                Decimal(self.area) * self.SQFT_PER_GAJ
            )

        return self._rounded_area(self.area)

    @property
    def display_area_gaj(self):
        if self.area_gaj is not None:
            return self.area_gaj

        if self.area is None:
            return None

        if self.area_unit == "gaj":
            return self._rounded_area(self.area)

        return self._rounded_area(
            Decimal(self.area) / self.SQFT_PER_GAJ
        )

    def _location_text(self):
        return ", ".join(
            str(part)
            for part in [
                getattr(self.city, "name", ""),
                getattr(self.state, "name", ""),
            ]
            if part
        )

    def build_seo_title(self):
        parts = [
            self.get_purpose_display(),
            self._area_for_title(),
            getattr(self.property_type, "name", ""),
        ]
        title = " ".join(str(part) for part in parts if part)

        location = self._location_text()
        if location:
            title = f"{title} in {location}" if title else location

        return title[:255] or "Property Listing"

    def build_seo_description(self):
        property_type = getattr(self.property_type, "name", "property")
        city = getattr(self.city, "name", "")
        state = getattr(self.state, "name", "")
        purpose = self.get_purpose_display().lower()
        price = self._clean_decimal_display(self.price)
        sqft = self._clean_decimal_display(self.area_sqft)
        gaj = self._clean_decimal_display(self.area_gaj)
        location = self._location_text()

        return (
            f"<p>{self.title} available for {purpose} in {location}. "
            f"This {property_type} has {sqft} sqft / {gaj} gaj area "
            f"with price Rs. {price}.</p>"
            f"<p>Contact Brij Vas for verified property details, site visit "
            f"and real estate guidance in {city}, {state}.</p>"
        )

    def save(self, *args, **kwargs):
        if self.area is not None:
            if self.area_unit == "gaj":
                self.area_gaj = self._rounded_area(self.area)
                self.area_sqft = self._rounded_area(
                    Decimal(self.area) * self.SQFT_PER_GAJ
                )
            else:
                self.area_sqft = self._rounded_area(self.area)
                self.area_gaj = self._rounded_area(
                    Decimal(self.area) / self.SQFT_PER_GAJ
                )

        if not self.title:
            self.title = self.build_seo_title()

        if not self.address:
            self.address = self._location_text()

        if not self.description:
            self.description = self.build_seo_description()

        if not self.slug:
            parts = [
                self.title,
                getattr(self.property_type, "name", ""),
                "in",
                getattr(self.city, "name", ""),
                getattr(self.state, "name", ""),
            ]
            self.slug = unique_slug(
                self,
                " ".join(str(part) for part in parts if part),
                fallback="property"
            )

        super().save(*args, **kwargs)
        optimize_uploaded_image(
            self.featured_image,
            max_size=(1600, 1200),
            target_kb=450
        )

    def get_absolute_url(self):
        return reverse(

            "property_detail",

            kwargs={"slug": self.slug}

        )

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

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        optimize_uploaded_image(
            self.image,
            max_size=(1600, 1200),
            target_kb=450
        )


class PropertyView(models.Model):
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="view_logs"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )

    session_key = models.CharField(
        max_length=40,
        blank=True,
        db_index=True
    )

    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True
    )

    user_agent_hash = models.CharField(
        max_length=64,
        blank=True,
        db_index=True
    )

    visitor_key = models.CharField(
        max_length=96,
        blank=True,
        db_index=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "property",
                    "user",
                ]
            ),
            models.Index(
                fields=[
                    "property",
                    "session_key",
                ]
            ),
            models.Index(
                fields=[
                    "property",
                    "visitor_key",
                ]
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "property",
                    "visitor_key",
                ],
                name="unique_property_visitor_view"
            )
        ]

    def __str__(self):
        return f"{self.property_id} view"


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


class Wishlist(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='wishlists'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        unique_together = (
            'user',
            'property'
        )

    def __str__(self):
        return f"{self.user} - {self.property}"


class CompareProperty(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.property.title


class PropertyReview(models.Model):
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='reviews'
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    rating = models.PositiveSmallIntegerField()

    review = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.property.title} - {self.rating}"


@property
def average_rating(self):
    reviews = self.reviews.all()

    if reviews.exists():
        return round(
            sum(r.rating for r in reviews) /
            reviews.count(),
            1
        )

    return 0

from saas.uploads import tenant_upload_path
from saas.models import TenantOwnedModel
from django.db import models


class SiteSetting(TenantOwnedModel):
    class Meta:
        constraints = [models.UniqueConstraint(fields=['tenant'], name='one_site_setting_per_tenant')]

    tagline = models.CharField(max_length=180, default='Find your next property')
    about_text = models.TextField(blank=True)
    primary_color = models.CharField(max_length=7, default='#146b50')

    site_name = models.CharField(max_length=200)

    logo = models.ImageField(
        upload_to=tenant_upload_path, blank=True
    )

    favicon = models.ImageField(
        upload_to=tenant_upload_path, blank=True
    )

    email = models.EmailField()

    phone = models.CharField(max_length=20)

    whatsapp = models.CharField(max_length=20)

    state = models.CharField(max_length=100, blank=True)

    address = models.TextField()

    facebook = models.URLField(blank=True)

    instagram = models.URLField(blank=True)

    youtube = models.URLField(blank=True)

    google_analytics_id = models.CharField(max_length=40, blank=True)

    google_ads_id = models.CharField(max_length=40, blank=True)

    google_site_verification = models.CharField(max_length=160, blank=True)

    custom_head_scripts = models.TextField(blank=True)

    def __str__(self):
        return self.site_name


class Contact(TenantOwnedModel):
    name = models.CharField(max_length=200)

    email = models.EmailField()

    phone = models.CharField(
        max_length=20,
        blank=True
    )

    subject = models.CharField(
        max_length=255,
        blank=True
    )

    message = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    is_read = models.BooleanField(
        default=False
    )

    def __str__(self):
        return self.name

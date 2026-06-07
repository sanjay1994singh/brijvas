from django.db import models


class SiteSetting(models.Model):
    site_name = models.CharField(max_length=200)

    logo = models.ImageField(
        upload_to='settings/'
    )

    favicon = models.ImageField(
        upload_to='settings/'
    )

    email = models.EmailField()

    phone = models.CharField(max_length=20)

    whatsapp = models.CharField(max_length=20)

    address = models.TextField()

    facebook = models.URLField(blank=True)

    instagram = models.URLField(blank=True)

    youtube = models.URLField(blank=True)

    def __str__(self):
        return self.site_name


class Contact(models.Model):
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

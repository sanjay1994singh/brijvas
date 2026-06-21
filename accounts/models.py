from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    USER_TYPE = (
        ('owner', 'Seller / Owner'),
        ('agent', 'Agent'),
        ('buyer', 'Buyer'),
    )

    phone = models.CharField(max_length=20, blank=True)

    address = models.TextField(blank=True)

    city = models.CharField(max_length=100, blank=True)

    state = models.CharField(max_length=100, blank=True)

    country = models.CharField(
        max_length=100,
        default="India",
        blank=True
    )

    profile_image = models.ImageField(
        upload_to='users/',
        blank=True,
        null=True
    )

    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPE,
        default='buyer'
    )

    is_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = (
        "username",
        "email",
        "phone",
        "city",
        "state",
        "country",
        "user_type",
        "is_verified",
        "is_staff",
    )

    list_filter = (
        "user_type",
        "is_verified",
        "is_staff",
    )

    search_fields = (
        "username",
        "email",
        "phone",
        "city",
        "state",
        "country",
        "first_name",
        "last_name",
    )

    list_editable = (
        "user_type",
        "is_verified",
    )

    fieldsets = DjangoUserAdmin.fieldsets + (
        (
            "Brij Vas Profile",
            {
                "fields": (
                    "phone",
                    "address",
                    "city",
                    "state",
                    "profile_image",
                    "user_type",
                    "is_verified",
                )
            },
        ),
    )

from django.contrib import admin
from .models import State, City


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    readonly_fields = (
        "slug",
    )

    list_display = (
        "name",
        "slug",
    )

    search_fields = (
        "name",
    )


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    readonly_fields = (
        "slug",
    )

    list_display = (
        "name",
        "state",
        "slug",
    )

    list_filter = (
        "state",
    )

    search_fields = (
        "name",
        "state__name",
    )

from django.contrib import admin
from .models import City, District, State


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    readonly_fields = (
        "slug",
    )

    list_display = (
        "name",
        "tenant",
        "slug",
    )

    list_filter = (
        "tenant",
    )

    search_fields = (
        "name",
    )


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    readonly_fields = (
        "slug",
    )

    list_display = (
        "name",
        "state",
        "tenant",
        "slug",
    )

    list_filter = (
        "state",
        "tenant",
    )

    search_fields = (
        "name",
        "state__name",
        "tenant__name",
    )


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    readonly_fields = (
        "slug",
    )

    list_display = (
        "name",
        "district",
        "state",
        "tenant",
        "slug",
    )

    list_filter = (
        "state",
        "district",
        "tenant",
    )

    search_fields = (
        "name",
        "district__name",
        "state__name",
        "tenant__name",
    )

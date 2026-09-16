from django.urls import path
from . import views

urlpatterns = [

    path(
        "",
        views.dashboard,
        name="dashboard"
    ),

    path(
        "add-property/",
        views.add_property,
        name="add_property"
    ),

    path(
        "subscription/",
        views.subscription,
        name="dashboard_subscription"
    ),

    path(
        "locations/districts/add/",
        views.add_district,
        name="dashboard_add_district"
    ),

    path(
        "locations/districts/",
        views.districts_for_state,
        name="dashboard_districts"
    ),

    path(
        "locations/cities/add/",
        views.add_city,
        name="dashboard_add_city"
    ),

    path(
        "locations/cities/",
        views.cities_for_district,
        name="dashboard_cities"
    ),

    path(
        "my-properties/",
        views.my_properties,
        name="my_properties"
    ),

    path(
        "edit-property/<int:id>/",
        views.edit_property,
        name="edit_property"
    ),

    path(
        "delete-property/<int:id>/",
        views.delete_property,
        name="delete_property"
    ),

    path(
        "enquiries/",
        views.enquiries,
        name="enquiries"
    ),

    path(
        "wishlist/",
        views.wishlist,
        name="wishlist"
    ),

    path(
        "agent/",
        views.agent_dashboard,
        name="agent_dashboard"
    ),

]

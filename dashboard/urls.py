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

from django.urls import path
from . import views

urlpatterns = [

    path(
        "",
        views.property_list,
        name="property_list"
    ),

    path(
        "search/",
        views.property_search,
        name="search_property"
    ),

    path(
        "compare/",
        views.compare_properties,
        name="compare_properties"
    ),

    path(
        "wishlist/add/<int:id>/",
        views.add_to_wishlist,
        name="add_to_wishlist"
    ),

    path(
        "wishlist/remove/<int:id>/",
        views.remove_from_wishlist,
        name="remove_wishlist"
    ),

    path(
        "compare/add/<int:id>/",
        views.add_to_compare,
        name="add_to_compare"
    ),

    path(
        "compare/remove/<int:id>/",
        views.remove_compare,
        name="remove_compare"
    ),

    path(
        "review/<int:property_id>/",
        views.add_review,
        name="add_review"
    ),



    path(
        "<slug:slug>/",
        views.property_detail,
        name="property_detail"
    ),

]

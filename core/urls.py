from django.urls import path
from . import views

urlpatterns = [

    path(
        "",
        views.home,
        name="home"
    ),
    path(
        "buy/<slug:slug>/",
        views.category_properties,
        name="category_properties"
    ),

    path(
        "about/",
        views.about,
        name="about"
    ),

    path(
        "contact/",
        views.contact,
        name="contact"
    ),

    path(
        "faq/",
        views.faq,
        name="faq"
    ),

    path(
        "privacy-policy/",
        views.privacy_policy,
        name="privacy_policy"
    ),

    path(
        "terms-and-conditions/",
        views.terms_conditions,
        name="terms_conditions"
    ),

    path(
        "robots.txt",
        views.robots_txt,
        name="robots_txt"
    ),

]

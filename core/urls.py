from django.urls import path
from . import views

urlpatterns = [

    path(
        "",
        views.home,
        name="home"
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

]

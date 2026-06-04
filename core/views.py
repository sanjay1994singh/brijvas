from django.shortcuts import render

from properties.models import (
    Property,
    PropertyType,
)

from blog.models import Blog


def home(request):
    featured_properties = Property.objects.filter(
        is_active=True,
        is_featured=True
    )[:8]

    latest_properties = Property.objects.filter(
        is_active=True
    ).order_by("-created_at")[:12]

    property_types = PropertyType.objects.all()

    latest_blogs = Blog.objects.filter(
        is_published=True
    )[:6]

    context = {

        "featured_properties": featured_properties,

        "latest_properties": latest_properties,

        "property_types": property_types,

        "latest_blogs": latest_blogs,

        "total_properties": Property.objects.count(),

    }

    return render(
        request,
        "home.html",
        context
    )


def about(request):
    return render(
        request,
        "core/about.html"
    )


def contact(request):
    return render(
        request,
        "core/contact.html"
    )


def faq(request):
    return render(
        request,
        "core/faq.html"
    )


def privacy_policy(request):
    return render(
        request,
        "core/privacy_policy.html"
    )


def terms_conditions(request):
    return render(
        request,
        "core/terms_conditions.html"
    )

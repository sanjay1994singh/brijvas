from django.shortcuts import (
    render,
    get_object_or_404,
    redirect
)
from properties.models import (
    Property,
    PropertyType,
)

from blog.models import Blog
from django.core.paginator import Paginator

from django.contrib import messages

from .models import Contact
from locations.models import City


def home(request):
    featured_properties = Property.objects.filter(
        is_active=True,
        is_featured=True
    )[:8]

    latest_properties = Property.objects.filter(
        is_active=True
    ).order_by("-created_at")[:12]

    cities = City.objects.all()
    property_types = PropertyType.objects.all()

    latest_blogs = Blog.objects.filter(
        is_published=True
    )[:6]

    context = {

        "featured_properties": featured_properties,

        "latest_properties": latest_properties,

        "cities": cities,

        "property_types": property_types,

        "latest_blogs": latest_blogs,

        "total_properties": Property.objects.count(),

    }

    return render(
        request,
        "home.html",
        context
    )


def category_properties(request, slug):
    category = get_object_or_404(
        PropertyType,
        slug=slug
    )

    properties = Property.objects.filter(
        property_type=category,
        is_active=True
    )

    paginator = Paginator(
        properties,
        12
    )

    page = request.GET.get("page")

    properties = paginator.get_page(page)

    context = {

        "category": category,

        "properties": properties

    }

    return render(request, "properties/category_properties.html", context)


def about(request):
    return render(
        request,
        "core/about.html"
    )


def contact(request):
    if request.method == "POST":
        Contact.objects.create(

            name=request.POST.get("name"),

            email=request.POST.get("email"),

            phone=request.POST.get("phone"),

            subject=request.POST.get("subject"),

            message=request.POST.get("message")

        )

        messages.success(
            request,
            "Thank you! We will contact you soon."
        )

        return redirect("contact")

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

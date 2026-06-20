from django.shortcuts import (
    render,
    get_object_or_404,
    redirect
)
from properties.models import (
    Property,
    PropertyType,
)
from django.http import HttpResponse

from blog.models import Blog
from django.core.paginator import Paginator

from django.contrib import messages

from .models import Contact
from locations.models import City
from accounts.models import User


def home(request):
    latest_properties = Property.objects.filter(
        is_active=True
    ).order_by("-created_at")[:12]

    cities = City.objects.all()
    property_types = PropertyType.objects.all()

    latest_blogs = Blog.objects.filter(
        is_published=True
    )[:6]

    context = {

        "latest_properties": latest_properties,

        "cities": cities,

        "property_types": property_types,

        "latest_blogs": latest_blogs,

        "total_properties": Property.objects.count(),

        "total_agents": User.objects.filter(
            user_type="agent"
        ).count(),

        "total_cities": cities.count(),

        "total_users": User.objects.count(),

    }

    return render(
        request,
        "home.html",
        context
    )

def google_verify(request):
    return render(
        request,
        "google90e7d13ae9f2d42d.html"
    )

def robots_txt(request):
    lines = [
        "User-agent: *",
        "Allow: /",
        "",
        "Sitemap: https://brijvas.com/sitemap.xml",
    ]

    return HttpResponse(
        "\n".join(lines),
        content_type="text/plain"
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

from saas.scoping import scoped
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
    if request.tenant is None:
        from saas.views import index
        return index(request)
    latest_properties = scoped(Property, request.tenant).filter(
        is_active=True
    ).order_by("-created_at")[:12]

    cities = City.objects.all()
    property_types = scoped(PropertyType, request.tenant).all()

    latest_blogs = scoped(Blog, request.tenant).filter(
        is_published=True
    )[:6]

    context = {

        "latest_properties": latest_properties,

        "cities": cities,

        "property_types": property_types,

        "latest_blogs": latest_blogs,

        "total_properties": scoped(Property, request.tenant).count(),

        "total_agents": User.objects.filter(
            memberships__tenant=request.tenant, memberships__role="agent", memberships__is_active=True
        ).count(),

        "total_cities": cities.count(),

        "total_users": User.objects.filter(memberships__tenant=request.tenant, memberships__is_active=True).count(),

    }

    return render(
        request,
        "home.html" if request.tenant.slug == "brijvas" else "saas/storefront.html",
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
        f"Sitemap: {request.scheme}://{request.get_host()}/sitemap.xml",
    ]

    return HttpResponse(
        "\n".join(lines),
        content_type="text/plain"
    )


def category_properties(request, slug):
    category = get_object_or_404(
        scoped(PropertyType, request.tenant),
        slug=slug
    )

    properties = scoped(Property, request.tenant).filter(
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
        "core/about.html" if request.tenant.slug == "brijvas" else "saas/about.html"
    )


def contact(request):
    if request.method == "POST":
        from .forms import ContactForm
        form = ContactForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Please provide a valid name, email and message (maximum 5000 characters).')
            return render(request, 'saas/contact.html', {'form': form}, status=400)
        scoped(Contact, request.tenant).create(tenant=request.tenant,

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
        "core/contact.html" if request.tenant.slug == "brijvas" else "saas/contact.html"
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


def tenant_sitemap(request):
    from django.contrib.sitemaps.views import sitemap
    from brijvas.urls import sitemaps
    return sitemap(request, sitemaps={key: cls(request.tenant) if key != 'static' else cls() for key, cls in sitemaps.items()})

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
from django.conf import settings

from blog.models import Blog
from django.core.paginator import Paginator

from django.contrib import messages

from .models import Contact
from locations.models import City
from accounts.models import User


def is_platform_request(request):
    host = request.get_host().split(":")[0].lower().rstrip(".")
    return host in {item.lower().rstrip(".") for item in settings.SAAS_PLATFORM_HOSTS}


def platform_or_tenant_template(request, platform_template, tenant_template):
    if is_platform_request(request) or request.tenant is None:
        return platform_template
    return tenant_template


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
        "saas/storefront.html",
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
        platform_or_tenant_template(request, "saas/about.html", "core/about.html")
    )


def contact(request):
    from .forms import ContactForm
    template = platform_or_tenant_template(request, "saas/contact.html", "core/contact.html")
    if request.method == "POST":
        form = ContactForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Please provide a valid name, email and message (maximum 5000 characters).')
            return render(request, template, {'form': form}, status=400)
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
        template,
        {'form': ContactForm()}
    )


def faq(request):
    return render(
        request,
        platform_or_tenant_template(request, "saas/faq.html", "core/faq.html")
    )


def privacy_policy(request):
    return render(
        request,
        platform_or_tenant_template(request, "saas/privacy_policy.html", "core/privacy_policy.html")
    )


def terms_conditions(request):
    return render(
        request,
        platform_or_tenant_template(request, "saas/terms_conditions.html", "core/terms_conditions.html")
    )


def refund_policy(request):
    return render(
        request,
        platform_or_tenant_template(request, "saas/refund_policy.html", "core/refund_policy.html")
    )


def billing_policy(request):
    return render(
        request,
        platform_or_tenant_template(request, "saas/billing_policy.html", "core/billing_policy.html")
    )


def grievance(request):
    return render(
        request,
        platform_or_tenant_template(request, "saas/grievance.html", "core/grievance.html")
    )


def disclaimer(request):
    return render(
        request,
        platform_or_tenant_template(request, "saas/disclaimer.html", "core/disclaimer.html")
    )


def tenant_sitemap(request):
    from django.contrib.sitemaps.views import sitemap
    from brijvas.urls import sitemaps
    return sitemap(request, sitemaps={key: cls(request.tenant) if key != 'static' else cls() for key, cls in sitemaps.items()})

from django.shortcuts import (
    render,
    get_object_or_404,
    redirect
)

from django.db.models import Q
from django.core.paginator import Paginator

from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .models import (
    Property,
    PropertyType,
    Wishlist,
    CompareProperty,
    PropertyReview
)

from enquiries.forms import EnquiryForm


def property_list(request):
    properties = Property.objects.filter(
        is_active=True
    ).select_related(
        "city",
        "property_type"
    )

    cities = Property.objects.values_list(
        "city__name",
        flat=True
    ).distinct()

    property_types = PropertyType.objects.all()

    paginator = Paginator(
        properties,
        12
    )

    page = request.GET.get("page")

    properties = paginator.get_page(page)

    context = {
        "properties": properties,
        "cities": cities,
        "property_types": property_types,
    }

    return render(
        request,
        "properties/property_list.html",
        context
    )


def property_search(request):
    properties = Property.objects.filter(
        is_active=True
    )

    keyword = request.GET.get("keyword")

    city = request.GET.get("city")

    property_type = request.GET.get("type")

    purpose = request.GET.get("purpose")

    if keyword:
        properties = properties.filter(

            Q(title__icontains=keyword) |

            Q(description__icontains=keyword)

        )

    if city:
        properties = properties.filter(
            city__slug=city
        )

    if property_type:
        properties = properties.filter(
            property_type__slug=property_type
        )

    if purpose:
        properties = properties.filter(
            purpose=purpose
        )

    paginator = Paginator(
        properties,
        12
    )

    page = request.GET.get("page")

    properties = paginator.get_page(page)

    context = {

        "properties": properties,

    }

    return render(
        request,
        "properties/property_list.html",
        context
    )


def property_detail(request, slug):
    property = get_object_or_404(
        Property,
        slug=slug,
        is_active=True
    )

    property.views += 1

    property.save(
        update_fields=["views"]
    )

    related_properties = Property.objects.filter(
        property_type=property.property_type,
        is_active=True
    ).exclude(
        id=property.id
    )[:6]

    reviews = PropertyReview.objects.filter(
        property=property
    )

    form = EnquiryForm()

    context = {

        "property": property,

        "related_properties": related_properties,

        "reviews": reviews,

        "form": form,

    }

    return render(

        request,

        "properties/property_detail.html",

        context

    )


@login_required
def add_review(request, property_id):
    property = get_object_or_404(
        Property,
        id=property_id
    )

    if request.method == "POST":
        rating = request.POST.get(
            "rating"
        )

        review = request.POST.get(
            "review"
        )

        PropertyReview.objects.create(

            property=property,

            user=request.user,

            rating=rating,

            review=review

        )

        messages.success(

            request,

            "Review added successfully."

        )

    return redirect(
        "property_detail",
        slug=property.slug
    )


@login_required
def add_to_wishlist(request, id):
    property = get_object_or_404(
        Property,
        id=id
    )

    Wishlist.objects.get_or_create(

        user=request.user,

        property=property

    )

    messages.success(
        request,
        "Added to wishlist."
    )

    return redirect(
        "property_detail",
        slug=property.slug
    )


@login_required
def remove_from_wishlist(request, id):
    Wishlist.objects.filter(

        user=request.user,

        property_id=id

    ).delete()

    messages.success(
        request,
        "Removed from wishlist."
    )

    return redirect(
        "wishlist"
    )


@login_required
def add_to_compare(request, id):
    property = get_object_or_404(
        Property,
        id=id
    )

    count = CompareProperty.objects.filter(

        user=request.user

    ).count()

    if count >= 4:
        messages.error(

            request,

            "Maximum 4 properties allowed."

        )

        return redirect(
            "property_detail",
            slug=property.slug
        )

    CompareProperty.objects.get_or_create(

        user=request.user,

        property=property

    )

    messages.success(
        request,
        "Added to compare."
    )

    return redirect(
        "property_detail",
        slug=property.slug
    )


@login_required
def compare_properties(request):
    compare_items = CompareProperty.objects.filter(
        user=request.user
    )

    context = {

        "compare_items": compare_items

    }

    return render(

        request,

        "properties/compare.html",

        context

    )


@login_required
def remove_compare(request, id):
    CompareProperty.objects.filter(

        user=request.user,

        property_id=id

    ).delete()

    return redirect(
        "compare_properties"
    )

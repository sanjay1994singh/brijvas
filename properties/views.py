from django.shortcuts import (
    render,
    get_object_or_404,
    redirect
)

from difflib import SequenceMatcher

from django.db.models import Q
from django.core.paginator import Paginator
from django.http import Http404

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
from core.seo import absolute_url, clean_excerpt, seo_slugify
from locations.models import City


def _slug_similarity(left, right):
    left = str(left or "").strip("-")
    right = str(right or "").strip("-")

    if not left or not right:
        return 0

    ratio = SequenceMatcher(None, left, right).ratio()
    left_tokens = {token for token in left.split("-") if len(token) > 2}
    right_tokens = {token for token in right.split("-") if len(token) > 2}

    if not left_tokens or not right_tokens:
        return ratio

    overlap = len(left_tokens & right_tokens) / len(left_tokens | right_tokens)
    return (ratio * 0.65) + (overlap * 0.35)


def _find_similar_property_by_slug(slug):
    requested_slug = seo_slugify(
        slug,
        fallback="property",
        max_length=120
    )

    best_property = None
    best_score = 0

    properties = Property.objects.filter(
        is_active=True
    ).select_related(
        "property_type",
        "city",
        "state"
    ).only(
        "id",
        "title",
        "slug",
        "property_type__name",
        "city__name",
        "state__name"
    )

    for property_obj in properties:
        parts = [
            property_obj.title,
            getattr(property_obj.property_type, "name", ""),
            "in",
            getattr(property_obj.city, "name", ""),
            getattr(property_obj.state, "name", ""),
        ]
        candidate_text = " ".join(str(part) for part in parts if part)
        candidate_slug = seo_slugify(
            candidate_text,
            fallback=property_obj.slug,
            max_length=120
        )

        score = max(
            _slug_similarity(requested_slug, property_obj.slug),
            _slug_similarity(requested_slug, candidate_slug)
        )

        if score > best_score:
            best_score = score
            best_property = property_obj

    if best_property and best_score >= 0.52:
        return best_property

    return None


def property_list(request):
    properties = Property.objects.filter(
        is_active=True
    ).select_related(
        "city",
        "property_type"
    )

    cities = City.objects.filter(
        property__is_active=True
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
    ).select_related(
        "city",
        "property_type"
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

    cities = City.objects.filter(
        property__is_active=True
    ).distinct()

    property_types = PropertyType.objects.all()

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


def property_detail(request, slug):
    try:
        property = Property.objects.get(
            slug=slug,
            is_active=True
        )
    except Property.DoesNotExist:
        similar_property = _find_similar_property_by_slug(slug)

        if similar_property:
            return redirect(
                "property_detail",
                slug=similar_property.slug,
                permanent=True
            )

        raise Http404("No Property matches the given query.")

    # Inquiry Submit

    if request.method == "POST":

        form = EnquiryForm(request.POST)

        if form.is_valid():

            enquiry = form.save(commit=False)

            enquiry.property = property

            if request.user.is_authenticated:
                enquiry.user = request.user

            enquiry.save()

            messages.success(
                request,
                "Your enquiry has been submitted successfully."
            )

            return redirect(
                "property_detail",
                slug=property.slug
            )

    else:

        form = EnquiryForm()

    # Views Counter

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

    location_text = ", ".join(
        part for part in [
            property.city.name,
            property.state.name,
        ] if part
    )
    property_seo_title = (
        f"{property.title} | {property.get_purpose_display()} "
        f"{property.property_type.name} in {location_text}"
    )
    property_seo_description = clean_excerpt(
        property.description,
        words=24
    ) or (
        f"{property.property_type.name} for {property.get_purpose_display().lower()} "
        f"in {location_text}. Area {property.area} {property.area_unit}, "
        f"price Rs {property.price}."
    )
    property_image_url = absolute_url(
        property.featured_image.url if property.featured_image else "",
        request=request
    )

    context = {

        "property": property,

        "related_properties": related_properties,

        "reviews": reviews,

        "form": form,

        "property_seo_title": property_seo_title,

        "property_seo_description": property_seo_description,

        "property_image_url": property_image_url,

        "property_canonical_url": absolute_url(
            property.get_absolute_url(),
            request=request
        ),

        "property_location_text": location_text,

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


def property_type(request, slug):
    return redirect(
        "category_properties",
        slug=slug
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

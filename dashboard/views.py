from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

from django.contrib.auth.decorators import login_required
from django.contrib import messages

from properties.models import (
    Property,
    Wishlist
)

from enquiries.models import Enquiry

from properties.forms import PropertyForm


@login_required
def dashboard(request):
    properties = Property.objects.filter(
        user=request.user
    )

    total_properties = properties.count()

    total_views = sum(
        properties.values_list(
            "views",
            flat=True
        )
    )

    total_enquiries = Enquiry.objects.filter(
        property__user=request.user
    ).count()

    featured_count = properties.filter(
        is_featured=True
    ).count()

    recent_properties = properties.order_by(
        "-created_at"
    )[:10]

    context = {

        "total_properties": total_properties,

        "total_views": total_views,

        "total_enquiries": total_enquiries,

        "featured_count": featured_count,

        "recent_properties": recent_properties,

    }

    return render(
        request,
        "dashboard/dashboard.html",
        context
    )


@login_required
def add_property(request):
    if request.method == "POST":

        form = PropertyForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():
            property_obj = form.save(
                commit=False
            )

            property_obj.user = request.user

            property_obj.save()

            form.save_m2m()

            messages.success(
                request,
                "Property added successfully."
            )

            return redirect(
                "my_properties"
            )

    else:

        form = PropertyForm()

    return render(
        request,
        "dashboard/add_property.html",
        {
            "form": form
        }
    )


@login_required
def my_properties(request):
    properties = Property.objects.filter(
        user=request.user
    ).order_by(
        "-created_at"
    )

    return render(
        request,
        "dashboard/my_properties.html",
        {
            "properties": properties
        }
    )


@login_required
def edit_property(request, id):
    property_obj = get_object_or_404(
        Property,
        id=id,
        user=request.user
    )

    if request.method == "POST":

        form = PropertyForm(

            request.POST,

            request.FILES,

            instance=property_obj

        )

        if form.is_valid():
            form.save()

            messages.success(

                request,

                "Property updated successfully."

            )

            return redirect(
                "my_properties"
            )

    else:

        form = PropertyForm(
            instance=property_obj
        )

    return render(
        request,
        "dashboard/edit_property.html",
        {
            "form": form,
            "property": property_obj
        }
    )


@login_required
def delete_property(request, id):
    property_obj = get_object_or_404(

        Property,

        id=id,

        user=request.user

    )

    property_obj.delete()

    messages.success(

        request,

        "Property deleted successfully."

    )

    return redirect(
        "my_properties"
    )


@login_required
def enquiries(request):
    enquiries = Enquiry.objects.filter(

        property__user=request.user

    ).select_related(

        "property"

    ).order_by(

        "-created_at"

    )

    return render(

        request,

        "dashboard/enquiries.html",

        {
            "enquiries": enquiries
        }

    )


@login_required
def wishlist(request):
    wishlist = Wishlist.objects.filter(

        user=request.user

    ).select_related(

        "property"

    )

    context = {

        "wishlist": [

            item.property
            for item in wishlist
        ]

    }

    return render(

        request,

        "dashboard/wishlist.html",

        context

    )


@login_required
def agent_dashboard(request):
    if request.user.user_type != "agent":
        return redirect(
            "dashboard"
        )

    properties = Property.objects.filter(
        user=request.user
    )

    context = {

        "properties": properties,

        "total_properties": properties.count(),

        "total_views": sum(
            properties.values_list(
                "views",
                flat=True
            )
        ),

        "total_enquiries": Enquiry.objects.filter(
            property__user=request.user
        ).count(),

    }

    return render(

        request,

        "dashboard/agent_dashboard.html",

        context

    )

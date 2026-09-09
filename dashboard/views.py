from functools import wraps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from properties.models import Property, Wishlist
from properties.forms import PropertyForm
from enquiries.models import Enquiry
from saas.scoping import scoped
from saas.services import save_listing, subscription_for


def approved(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.tenant or not request.membership:
            raise PermissionDenied('Business membership required.')
        if request.membership.role in ('seller', 'agent') and not request.membership.is_approved:
            return render(request, 'dashboard/pending_approval.html')
        return view(request, *args, **kwargs)
    return wrapped


def listings_for(request):
    queryset = scoped(Property, request.tenant)
    if not request.membership or not request.membership.can_manage:
        queryset = queryset.filter(user=request.user)
    return queryset


@approved
def dashboard(request):
    properties = listings_for(request)
    enquiries = scoped(Enquiry, request.tenant)
    if not request.membership.can_manage:
        enquiries = enquiries.filter(property__user=request.user)
    return render(request, 'dashboard/dashboard.html', {
        'total_properties': properties.count(),
        'total_views': sum(properties.values_list('views', flat=True)),
        'total_enquiries': enquiries.count(),
        'featured_count': properties.filter(is_featured=True).count(),
        'recent_properties': properties.order_by('-created_at')[:10],
    })


@approved
def add_property(request):
    if not request.membership.can_list:
        raise PermissionDenied('Approved seller or staff access required.')
    form = PropertyForm(request.POST or None, request.FILES or None, tenant=request.tenant)
    if request.method == 'POST' and form.is_valid():
        try:
            save_listing(form=form, tenant=request.tenant, user=request.user, membership=request.membership)
            messages.success(request, 'Property saved.' if request.membership.can_manage else 'Property submitted for review.')
            return redirect('my_properties')
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(request, 'dashboard/add_property.html', {'form': form})


@approved
def my_properties(request):
    return render(request, 'dashboard/my_properties.html', {'properties': listings_for(request).order_by('-created_at')})


@approved
def edit_property(request, id):
    if not request.membership.can_list:
        raise PermissionDenied('Approved seller or staff access required.')
    obj = get_object_or_404(listings_for(request), pk=id)
    form = PropertyForm(request.POST or None, request.FILES or None, instance=obj, tenant=request.tenant)
    if request.method == 'POST' and form.is_valid():
        try:
            save_listing(form=form, tenant=request.tenant, user=request.user, membership=request.membership)
            messages.success(request, 'Property updated.')
            return redirect('my_properties')
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(request, 'dashboard/edit_property.html', {'form': form, 'property': obj})


@approved
@require_POST
def delete_property(request, id):
    if not request.membership.can_list:
        raise PermissionDenied('Approved seller or staff access required.')
    get_object_or_404(listings_for(request), pk=id).delete()
    messages.success(request, 'Property deleted.')
    return redirect('my_properties')


@approved
def enquiries(request):
    queryset = scoped(Enquiry, request.tenant)
    if not request.membership.can_manage:
        queryset = queryset.filter(property__user=request.user)
    return render(request, 'dashboard/enquiries.html', {'enquiries': queryset.select_related('property').order_by('-created_at')})


@login_required
def wishlist(request):
    queryset = scoped(Wishlist, request.tenant).filter(user=request.user).select_related('property')
    return render(request, 'dashboard/wishlist.html', {'wishlist': [item.property for item in queryset]})


@approved
def agent_dashboard(request):
    return dashboard(request)

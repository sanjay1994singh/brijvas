from functools import wraps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from locations.models import City, District, State
from properties.models import Property, Wishlist
from properties.forms import PropertyForm
from enquiries.models import Enquiry
from saas import billing
from saas.models import BillingOrder, Plan
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
    subscription = getattr(request.tenant, 'subscription', None)
    return render(request, 'dashboard/dashboard.html', {
        'total_properties': properties.count(),
        'total_views': sum(properties.values_list('views', flat=True)),
        'total_enquiries': enquiries.count(),
        'featured_count': properties.filter(is_featured=True).count(),
        'recent_properties': properties.order_by('-created_at')[:10],
        'subscription': subscription,
    })


@approved
def subscription(request):
    if not request.membership.can_manage:
        raise PermissionDenied('Business administrator access required.')
    subscription_obj = getattr(request.tenant, 'subscription', None)
    current_plan = subscription_obj.plan if subscription_obj else None
    plans = []
    for plan in Plan.objects.filter(is_active=True).order_by('monthly_amount', 'listing_limit', 'name'):
        breakup = billing.price_breakup(plan, tenant=request.tenant)
        is_current = current_plan and current_plan.pk == plan.pk
        is_upgrade = not current_plan or plan.monthly_amount > current_plan.monthly_amount or plan.listing_limit > current_plan.listing_limit
        plans.append({
            'plan': plan,
            'breakup': breakup,
            'amount_rupees': breakup['amount'] / 100,
            'display_price_rupees': plan.discounted_price,
            'subtotal_rupees': breakup['subtotal_amount'] / 100,
            'discount_rupees': breakup['discount_amount'] / 100,
            'plan_discount_rupees': breakup['plan_discount_amount'] / 100,
            'upgrade_credit_rupees': breakup['upgrade_credit_amount'] / 100,
            'last_paid_rupees': breakup['current_paid_amount'] / 100,
            'current_paid_taxable_rupees': breakup['current_paid_taxable_amount'] / 100,
            'taxable_rupees': breakup['taxable_amount'] / 100,
            'gst_rupees': breakup['gst_amount'] / 100,
            'is_current': is_current,
            'is_upgrade': is_upgrade,
        })
    latest_pending = BillingOrder.objects.filter(tenant=request.tenant, status='pending').select_related('plan').order_by('-created_at').first()
    latest_paid = BillingOrder.objects.filter(tenant=request.tenant, status='paid').select_related('plan').order_by('-paid_at', '-created_at').first()
    orders = []
    for order in (latest_pending, latest_paid):
        if order and order.pk not in {item.pk for item in orders}:
            orders.append(order)
    return render(request, 'dashboard/subscription.html', {
        'subscription': subscription_obj,
        'plans': plans,
        'orders': orders,
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
def districts_for_state(request):
    districts = District.objects.filter(
        tenant=request.tenant,
        state_id=request.GET.get('state'),
    ).order_by('name')
    return JsonResponse({
        'ok': True,
        'districts': [{'id': district.pk, 'name': district.name} for district in districts],
    })


@approved
def cities_for_district(request):
    cities = City.objects.filter(
        tenant=request.tenant,
        district_id=request.GET.get('district'),
    ).order_by('name')
    return JsonResponse({
        'ok': True,
        'cities': [{'id': city.pk, 'name': city.name} for city in cities],
    })


@approved
@require_POST
def add_district(request):
    state = get_object_or_404(State, pk=request.POST.get('state'))
    name = (request.POST.get('name') or '').strip()
    if not name:
        return JsonResponse({'ok': False, 'error': 'Enter district name.'}, status=400)
    district = District.objects.filter(tenant=request.tenant, state=state, name__iexact=name).first()
    if not district:
        district = District.objects.create(tenant=request.tenant, state=state, name=name)
    return JsonResponse({'ok': True, 'district': {'id': district.pk, 'name': district.name}})


@approved
@require_POST
def add_city(request):
    district = get_object_or_404(District, pk=request.POST.get('district'), tenant=request.tenant)
    name = (request.POST.get('name') or '').strip()
    if not name:
        return JsonResponse({'ok': False, 'error': 'Enter city name.'}, status=400)
    city = City.objects.filter(tenant=request.tenant, district=district, name__iexact=name).first()
    if not city:
        city = City.objects.create(tenant=request.tenant, state=district.state, district=district, name=name)
    return JsonResponse({'ok': True, 'city': {'id': city.pk, 'name': city.name}})


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

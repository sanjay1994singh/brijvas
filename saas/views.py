import json
import hashlib
import hmac
from functools import wraps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from core.models import Contact, SiteSetting
from properties.models import Property
from . import billing
from .forms import DomainForm, MemberForm, SignupForm, SiteForm
from .models import AuditEvent, BillingOrder, Domain, Membership, Plan, Tenant
from .services import provision, subscription_for


def index(request):
    return render(request, 'saas/index.html', {'plans': Plan.objects.filter(is_active=True), 'trial_days': settings.SAAS_TRIAL_DAYS})


def signup(request):
    if request.tenant:
        return redirect(settings.SAAS_BASE_URL + '/saas/signup/')
    if request.user.is_authenticated:
        return redirect('saas_workspaces')
    initial = {}
    if request.method == 'GET':
        selected = Plan.objects.filter(slug=request.GET.get('plan'), is_active=True).first()
        if selected:
            initial['plan'] = selected
    form = SignupForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                user = form.save()
                tenant = provision(owner=user, name=form.cleaned_data['business_name'], slug=form.cleaned_data['site_slug'], plan=form.cleaned_data['plan'])
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('saas_business', slug=tenant.slug)
        except (ValidationError, IntegrityError) as exc:
            form.add_error(None, '; '.join(exc.messages) if isinstance(exc, ValidationError) else 'This username or website address was just taken. Please choose another.')
    return render(request, 'saas/form.html', {'form': form, 'heading': 'Launch your property website', 'button': 'Create my website'})


@login_required(login_url='saas_login')
def workspaces(request):
    memberships = request.user.memberships.filter(is_active=True, role__in=['owner', 'admin'], is_approved=True).select_related('tenant')
    return render(request, 'saas/workspaces.html', {'memberships': memberships})


def business_admin(view):
    @login_required(login_url='saas_login')
    @wraps(view)
    def wrapped(request, slug, *args, **kwargs):
        tenant = get_object_or_404(Tenant, slug=slug)
        membership = Membership.objects.filter(tenant=tenant, user=request.user).first()
        if not membership or not membership.can_manage:
            return HttpResponseForbidden('Business administrator access required.')
        if request.tenant and request.tenant.pk != tenant.pk:
            return HttpResponseForbidden('Open the correct business website.')
        try:
            return view(request, tenant, *args, **kwargs)
        except ValidationError as exc:
            messages.error(request, '; '.join(exc.messages))
            return redirect('saas_business', slug=tenant.slug)
    return wrapped


@business_admin
def business(request, tenant):
    return render(request, 'saas/business.html', {
        'business': tenant, 'subscription': getattr(tenant, 'subscription', None),
        'listing_count': Property.objects.filter(tenant=tenant).count(),
        'pending_count': Property.objects.filter(tenant=tenant, is_active=False).count(),
        'member_count': tenant.memberships.filter(is_active=True).count(),
        'events': tenant.events.order_by('-created_at')[:8],
        'orders': tenant.orders.order_by('-created_at')[:10],
        'plans': Plan.objects.filter(is_active=True),
        'payments_enabled': bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET),
    })


@business_admin
def branding(request, tenant):
    setting = get_object_or_404(SiteSetting, tenant=tenant)
    form = SiteForm(request.POST or None, request.FILES or None, instance=setting)
    if request.method == 'POST' and form.is_valid():
        try:
            subscription_for(tenant)
            from .uploads import ensure_storage
            with transaction.atomic():
                Tenant.objects.select_for_update().get(pk=tenant.pk)
                ensure_storage(tenant, sum(f.size for f in request.FILES.values()))
                form.save()
            AuditEvent.objects.create(tenant=tenant, actor=request.user, action='branding.updated')
            messages.success(request, 'Website settings saved.')
            return redirect('saas_business', slug=tenant.slug)
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(request, 'saas/form.html', {'form': form, 'business': tenant, 'heading': 'Website settings', 'button': 'Save settings'})


@business_admin
def members(request, tenant):
    form = MemberForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                Tenant.objects.select_for_update().get(pk=tenant.pk)
                sub = subscription_for(tenant)
                user = get_user_model().objects.filter(username=form.cleaned_data['username']).first()
                if not user:
                    raise ValidationError('This account does not exist. Ask the person to register on your website first.')
                existing = tenant.memberships.filter(user=user).first()
                if not existing:
                    raise ValidationError('This account must register on your business website first.')
                consumes_seat = existing.is_active and existing.is_approved and existing.role in ('owner', 'admin', 'agent')
                if not consumes_seat and tenant.memberships.filter(is_active=True, is_approved=True, role__in=['owner', 'admin', 'agent']).count() >= sub.plan.staff_limit:
                    raise ValidationError('Your staff limit has been reached.')
                if tenant.memberships.filter(user=user, role='owner').exists():
                    raise ValidationError('The business owner cannot be changed here.')
                Membership.objects.update_or_create(tenant=tenant, user=user, defaults={'role': form.cleaned_data['role'], 'is_active': True, 'is_approved': True})
                AuditEvent.objects.create(tenant=tenant, actor=request.user, action='member.added', detail=user.username)
            return redirect('saas_members', slug=tenant.slug)
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(request, 'saas/members.html', {'form': form, 'business': tenant, 'members': tenant.memberships.select_related('user')})


@business_admin
@require_POST
def member_action(request, tenant, pk):
    with transaction.atomic():
        Tenant.objects.select_for_update().get(pk=tenant.pk)
        sub = subscription_for(tenant)
        member = get_object_or_404(Membership, pk=pk, tenant=tenant)
        if member.role == 'owner' or member.user_id == request.user.pk:
            return HttpResponseForbidden('The owner or your own membership cannot be changed here.')
        if request.POST.get('action') == 'approve':
            if member.role in ('agent', 'admin') and not member.is_approved and tenant.memberships.filter(is_active=True, is_approved=True, role__in=['owner', 'admin', 'agent']).count() >= sub.plan.staff_limit:
                messages.error(request, 'Staff limit reached.')
                return redirect('saas_members', slug=tenant.slug)
            member.is_approved = True
        elif request.POST.get('action') == 'disable':
            member.is_active = False
        else:
            return HttpResponse(status=400)
        member.save()
        AuditEvent.objects.create(tenant=tenant, actor=request.user, action='member.' + request.POST['action'], detail=str(member.pk))
    return redirect('saas_members', slug=tenant.slug)


@business_admin
def listings(request, tenant):
    return render(request, 'saas/listings.html', {'business': tenant, 'listings': Property.objects.filter(tenant=tenant).select_related('user', 'city').order_by('-created_at')[:200]})


@business_admin
@require_POST
def listing_action(request, tenant, pk):
    subscription_for(tenant)
    if request.POST.get('action') not in ('publish', 'unpublish'):
        return HttpResponse(status=400)
    obj = get_object_or_404(Property, tenant=tenant, pk=pk)
    obj.is_active = request.POST.get('action') == 'publish'
    obj.save(update_fields=['is_active'])
    AuditEvent.objects.create(tenant=tenant, actor=request.user, action='listing.visibility', detail=str(obj.pk))
    return redirect('saas_listings', slug=tenant.slug)


@business_admin
def leads(request, tenant):
    from enquiries.models import Enquiry
    return render(request, 'saas/leads.html', {'business': tenant, 'leads': Enquiry.objects.filter(property__tenant=tenant).select_related('property').order_by('-created_at')[:200], 'contacts': Contact.objects.filter(tenant=tenant).order_by('-created_at')[:100]})


@business_admin
def domains(request, tenant):
    form = DomainForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            sub = subscription_for(tenant)
            if not sub.plan.custom_domain:
                raise ValidationError('Upgrade to a plan with custom domains.')
            if tenant.domains.count() >= 5:
                raise ValidationError('Maximum five domains per business.')
            Domain.objects.create(tenant=tenant, hostname=form.cleaned_data['hostname'])
            return redirect('saas_domains', slug=tenant.slug)
        except (ValidationError, IntegrityError) as exc:
            form.add_error(None, exc if isinstance(exc, ValidationError) else 'This domain is already registered.')
    return render(request, 'saas/domains.html', {'business': tenant, 'form': form, 'domains': tenant.domains.all(), 'target': settings.SAAS_DOMAIN_TARGET})


@business_admin
@require_POST
def verify_domain(request, tenant, pk):
    domain = get_object_or_404(Domain, tenant=tenant, pk=pk)
    import dns.resolver
    try:
        answers = dns.resolver.resolve(domain.txt_name, 'TXT', lifetime=5)
        values = [''.join(part.decode() for part in answer.strings) for answer in answers]
        if domain.txt_value not in values:
            raise ValueError('TXT token not found')
        domain.is_verified = True
        domain.error = ''
        domain.save(update_fields=['is_verified', 'error'])
        messages.success(request, 'Ownership verified. SSL activation is the next step; your platform URL remains available.')
    except Exception:
        messages.error(request, 'TXT verification record is not available yet. Check the record and retry.')
    return redirect('saas_domains', slug=tenant.slug)


@business_admin
@require_POST
def checkout(request, tenant):
    plan = get_object_or_404(Plan, pk=request.POST.get('plan'), is_active=True)
    try:
        order = billing.create_order(tenant, plan)
    except ValidationError as exc:
        messages.error(request, '; '.join(exc.messages))
        return redirect('saas_business', slug=tenant.slug)
    return render(request, 'saas/checkout.html', {'business': tenant, 'order': order, 'key_id': settings.RAZORPAY_KEY_ID})


@business_admin
@require_POST
def payment_verify(request, tenant):
    order = get_object_or_404(BillingOrder, tenant=tenant, provider_order=request.POST.get('razorpay_order_id'))
    try:
        billing.verify_signature(order.provider_order, request.POST.get('razorpay_payment_id', ''), request.POST.get('razorpay_signature', ''))
        billing.settle(order, request.POST.get('razorpay_payment_id', ''))
        messages.success(request, 'Payment verified. Your subscription is active.')
    except ValidationError as exc:
        messages.error(request, '; '.join(exc.messages))
    return redirect('saas_business', slug=tenant.slug)


@csrf_exempt
@require_POST
def webhook(request):
    secret = settings.RAZORPAY_WEBHOOK_SECRET
    signature = request.headers.get('X-Razorpay-Signature', '')
    if not secret or not hmac.compare_digest(hmac.new(secret.encode(), request.body, hashlib.sha256).hexdigest(), signature):
        return HttpResponse(status=400)
    try:
        payload = json.loads(request.body)
        if payload.get('event') not in ('payment.captured', 'order.paid'):
            return JsonResponse({'received': True})
        payment = payload['payload']['payment']['entity']
        order = BillingOrder.objects.filter(provider_order=payment['order_id']).first()
        if order:
            billing.settle(order, payment['id'])
    except (KeyError, TypeError, ValueError, ValidationError):
        return HttpResponse(status=400)
    return JsonResponse({'received': True})

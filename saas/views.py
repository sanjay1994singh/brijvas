import json
import hashlib
import hmac
from datetime import timedelta
from io import BytesIO
from functools import wraps
from urllib.parse import quote
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.core import signing
from django.core.mail import EmailMultiAlternatives
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from core.models import Contact, SiteSetting
from properties.models import Property
from . import billing
from .forms import DomainForm, MemberForm, SignupForm, SiteForm
from .models import AuditEvent, BillingOrder, Domain, Membership, PendingSignup, Plan, PurchaseAgreementAcceptance, Tenant
from .services import active_purchase_agreement, provision, record_purchase_agreement_acceptance, subscription_for
from .whatsapp import WHATSAPP_INVOICE_SIGNER_SALT


def latest_payment_history(tenant, limit=2):
    orders = []
    latest_paid = tenant.orders.filter(status='paid').order_by('-paid_at', '-created_at').first()
    latest_pending = tenant.orders.filter(status='pending').order_by('-created_at').first()
    for order in (latest_pending, latest_paid):
        if order and order.pk not in {item.pk for item in orders}:
            orders.append(order)
    return orders[:limit]


def _money(value):
    return f"Rs {value / 100:.2f}"


def _billing_months(value):
    try:
        months = int(value)
    except (TypeError, ValueError):
        months = 1
    return months if months in (1, 12, 24) else 1


def _cycle_label(months):
    if months == 12:
        return '1 year'
    if months == 24:
        return '2 years'
    return '1 month'


def _plan_json(plan, months=1):
    months = _billing_months(months)
    start = timezone.localdate()
    end = start + timedelta(days=billing.duration_days(months))
    breakup = billing.price_breakup(plan, months=months)
    return {
        'id': plan.pk,
        'name': plan.name,
        'billing_months': months,
        'cycle': _cycle_label(months),
        'start': start.strftime('%d %b %Y'),
        'end': end.strftime('%d %b %Y'),
        'listing_limit': plan.listing_limit,
        'staff_limit': plan.staff_limit,
        'storage_mb': plan.storage_mb,
        'custom_domain': plan.custom_domain,
        'trial_enabled': plan.trial_enabled,
        'trial_days': plan.trial_days,
        'amount_rupees': breakup['amount'] / 100,
        'subtotal_rupees': breakup['subtotal_amount'] / 100,
        'discount_rupees': breakup['discount_amount'] / 100,
        'gst_rupees': breakup['gst_amount'] / 100,
        'gst_percent': breakup['gst_percent'],
        'features': plan.active_features,
    }


def _invoice_pdf(order, tenant):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    billing_setting = billing.BillingSetting.current()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=24 * mm,
        bottomMargin=18 * mm,
        title=f"Invoice {order.uuid}",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Tiny", parent=styles["Normal"], fontSize=8.6, leading=11.4))
    styles.add(ParagraphStyle(name="Small", parent=styles["Normal"], fontSize=9.5, leading=13))
    styles.add(ParagraphStyle(name="BoldSmall", parent=styles["Small"], fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="InvoiceTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=34, leading=38, alignment=2))
    styles.add(ParagraphStyle(name="Brand", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=23, leading=25, alignment=0))

    invoice_no = f"PNX-{order.created_at:%Y%m%d}-{order.pk:05d}"
    issue_date = order.paid_at or order.created_at
    owner = tenant.owner
    period_start = order.paid_at or order.created_at
    cycle_label = _cycle_label(order.billing_months)
    period_end = period_start + timedelta(days=billing.duration_days(order.billing_months))

    seller_lines = [
        billing_setting.business_name,
        billing_setting.business_address,
        f"GSTIN: {billing_setting.gstin}",
        f"PAN: {billing_setting.pan}",
        f"CIN: {billing_setting.cin}",
        billing_setting.support_email,
        f"WhatsApp: {billing_setting.whatsapp_number}",
    ]
    seller = [Paragraph("Vistaflo", styles["Brand"])] + [Paragraph(line, styles["Tiny"]) for line in seller_lines if line]
    meta = [
        Paragraph("INVOICE", styles["InvoiceTitle"]),
        Paragraph(f"<b>INVOICE NO:</b> {invoice_no}", styles["Tiny"]),
        Paragraph(f"<b>ISSUE DATE:</b> {issue_date:%d %b %Y, %I:%M %p}", styles["Tiny"]),
        Paragraph("<b>STATUS:</b> PAID", styles["Tiny"]),
    ]
    story = [
        Table([[seller, meta]], colWidths=[106 * mm, 53 * mm], style=TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ])),
        Spacer(1, 20 * mm),
    ]

    billed_to = [
        Paragraph("<b>BILLED TO</b>", styles["Tiny"]),
        Paragraph(f"<b>{owner.get_full_name() or owner.username}</b>", styles["Tiny"]),
        Paragraph(tenant.name, styles["Tiny"]),
        Paragraph(owner.state or "-", styles["Tiny"]),
        Paragraph(f"Mobile: {owner.phone or '-'}", styles["Tiny"]),
    ]
    story += billed_to + [Spacer(1, 13 * mm)]

    items = [
        ["#", "DESCRIPTION", "QTY", "RATE", "AMOUNT"],
        [
            "01",
            Paragraph(
                f"<b>{order.plan.name}</b><br/>Website subscription - {cycle_label}<br/>"
                f"Period: {period_start:%d %b %Y} to {period_end:%d %b %Y}",
                styles["Tiny"],
            ),
            "1",
            _money(order.subtotal_amount),
            _money(order.subtotal_amount),
        ],
    ]
    table = Table(items, colWidths=[12 * mm, 92 * mm, 16 * mm, 23 * mm, 25 * mm])
    table.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 1, colors.black),
        ("LINEBELOW", (0, 0), (-1, 0), .7, colors.black),
        ("LINEBELOW", (0, -1), (-1, -1), .4, colors.lightgrey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.4),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    story += [table, Spacer(1, 14 * mm)]

    payment_details = [
        Paragraph("<b>PAYMENT DETAILS</b>", styles["Tiny"]),
        Paragraph("Reference", styles["Tiny"]),
        Paragraph(order.provider_payment or "-", styles["Tiny"]),
        Spacer(1, 5 * mm),
        Paragraph("<b>SUPPORT</b>", styles["Tiny"]),
        Paragraph("For billing corrections, contact support with your invoice number and payment reference.", styles["Tiny"]),
    ]
    totals_rows = [
        ["Subtotal", _money(order.subtotal_amount)],
    ]
    if order.discount_amount:
        totals_rows.append(["Discount / credit", _money(order.discount_amount)])
    if order.gst_amount:
        totals_rows.append([f"GST @ {order.gst_percent}%", _money(order.gst_amount)])
    totals_rows += [["Total", _money(order.amount)], ["Payment status", "PAID"]]
    totals = Table(totals_rows, colWidths=[46 * mm, 31 * mm])
    totals.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8.6),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, -2), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE", (0, -2), (-1, -2), .8, colors.black),
        ("LINEBELOW", (0, -2), (-1, -2), .8, colors.black),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story += [
        Table([[payment_details, totals]], colWidths=[88 * mm, 78 * mm], style=TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ])),
        Spacer(1, 24 * mm),
        Paragraph("Thank you for choosing Vistaflo. This invoice is generated electronically.", styles["Tiny"]),
    ]
    doc.build(story)
    return buffer.getvalue(), invoice_no


def send_signup_email(*, user, tenant):
    if not user.email:
        return
    login_url = tenant.public_url.rstrip('/') + '/accounts/login/'
    control_url = tenant.public_url.rstrip('/') + f'/manage/{tenant.slug}/'
    website_url = tenant.public_url
    subject = f'Your {tenant.name} website is ready'
    text = (
        f'Hello {user.username},\n\n'
        f'Your property website has been created successfully.\n\n'
        f'Business name: {tenant.name}\n'
        f'Website: {website_url}\n'
        f'Control panel: {control_url}\n'
        f'Login: {login_url}\n'
        f'Username: {user.username}\n'
        f'Email: {user.email}\n'
        f'Mobile: {user.phone}\n'
        'Password: Use the password you created during signup.\n\n'
        'Regards,\nVistaflo Team'
    )
    html = f"""
    <div style="margin:0;padding:28px;background:#f5f7f4;font-family:Arial,sans-serif;color:#172b24">
      <div style="max-width:620px;margin:auto;background:#ffffff;border:1px solid #dce5dd;border-radius:12px;overflow:hidden">
        <div style="background:#17634b;color:#ffffff;padding:24px 28px">
          <h1 style="margin:0;font-size:24px">Your property website is ready</h1>
          <p style="margin:8px 0 0">Welcome to Vistaflo, {user.username}.</p>
        </div>
        <div style="padding:28px">
          <p style="font-size:16px;line-height:1.6">Your business website for <strong>{tenant.name}</strong> has been created successfully.</p>
          <table style="width:100%;border-collapse:collapse;margin:22px 0">
            <tr><td style="padding:10px;border-bottom:1px solid #edf1ee;color:#66776d">Business name</td><td style="padding:10px;border-bottom:1px solid #edf1ee"><strong>{tenant.name}</strong></td></tr>
            <tr><td style="padding:10px;border-bottom:1px solid #edf1ee;color:#66776d">Website</td><td style="padding:10px;border-bottom:1px solid #edf1ee"><a href="{website_url}">{website_url}</a></td></tr>
            <tr><td style="padding:10px;border-bottom:1px solid #edf1ee;color:#66776d">Control panel</td><td style="padding:10px;border-bottom:1px solid #edf1ee"><a href="{control_url}">Open control panel</a></td></tr>
            <tr><td style="padding:10px;border-bottom:1px solid #edf1ee;color:#66776d">Login</td><td style="padding:10px;border-bottom:1px solid #edf1ee"><a href="{login_url}">{login_url}</a></td></tr>
            <tr><td style="padding:10px;border-bottom:1px solid #edf1ee;color:#66776d">Username</td><td style="padding:10px;border-bottom:1px solid #edf1ee">{user.username}</td></tr>
            <tr><td style="padding:10px;border-bottom:1px solid #edf1ee;color:#66776d">Email</td><td style="padding:10px;border-bottom:1px solid #edf1ee">{user.email}</td></tr>
            <tr><td style="padding:10px;border-bottom:1px solid #edf1ee;color:#66776d">Mobile</td><td style="padding:10px;border-bottom:1px solid #edf1ee">{user.phone}</td></tr>
          </table>
          <p style="font-size:14px;color:#66776d">Use the password you created during signup to sign in.</p>
        </div>
      </div>
    </div>
    """
    message = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, [user.email])
    message.attach_alternative(html, 'text/html')
    message.send(fail_silently=True)


def index(request):
    return render(request, 'saas/index.html', {'plans': Plan.objects.filter(is_active=True), 'trial_days': settings.SAAS_TRIAL_DAYS})


def signup(request):
    if request.tenant:
        return redirect(settings.SAAS_BASE_URL + '/accounts/signup/')
    if request.user.is_authenticated:
        return redirect('saas_workspaces')
    initial = {}
    if request.method == 'GET':
        selected = Plan.objects.filter(slug=request.GET.get('plan'), is_active=True).first()
        if selected:
            initial['plan'] = selected
    purchase_agreement = active_purchase_agreement()
    form = SignupForm(request.POST or None, initial=initial)
    if purchase_agreement:
        form.fields['accepted_purchase_terms'].label = purchase_agreement.checkbox_label
    if request.method == 'POST' and form.is_valid():
        try:
            plan = form.cleaned_data['plan']
            billing_months = form.cleaned_data['billing_months']
            if not plan.trial_enabled:
                pending = PendingSignup.objects.create(
                    business_name=form.cleaned_data['business_name'],
                    username=form.cleaned_data['username'],
                    email=form.cleaned_data['email'],
                    phone=form.cleaned_data['phone'],
                    state='',
                    password_hash=make_password(form.cleaned_data['password']),
                    plan=plan,
                    billing_months=billing_months,
                    **billing.persisted_breakup(billing.price_breakup(plan, months=billing_months)),
                )
                billing.create_pending_signup_order(pending)
                record_purchase_agreement_acceptance(
                    pending_signup=pending,
                    agreement=purchase_agreement,
                    request=request,
                )
                return redirect('saas_pending_checkout', signup_id=pending.uuid)
            with transaction.atomic():
                user = form.save()
                tenant = provision(owner=user, name=form.cleaned_data['business_name'], plan=plan, slug=form.cleaned_data['username'])
                record_purchase_agreement_acceptance(
                    user=user,
                    tenant=tenant,
                    agreement=purchase_agreement,
                    request=request,
                )
            send_signup_email(user=user, tenant=tenant)
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('saas_business', slug=tenant.slug)
        except (ValidationError, IntegrityError) as exc:
            form.add_error(None, '; '.join(exc.messages) if isinstance(exc, ValidationError) else 'This username or website address was just taken. Please choose another.')
    return render(request, 'saas/form.html', {
        'form': form,
        'heading': 'Launch your property website',
        'button': 'Create my website',
        'purchase_agreement': purchase_agreement,
        'signup_page': True,
    })


def signup_plan_detail(request, plan_id):
    plan = get_object_or_404(Plan.objects.prefetch_related('features'), pk=plan_id, is_active=True)
    return JsonResponse(_plan_json(plan, request.GET.get('months')))


def pending_checkout(request, signup_id):
    pending = get_object_or_404(PendingSignup.objects.select_related('plan'), uuid=signup_id)
    if pending.status == 'paid':
        tenant = Tenant.objects.filter(slug=pending.username).select_related('owner').first()
        if tenant:
            if tenant.owner:
                login(request, tenant.owner, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, 'Payment verified. Your website is ready.')
            return redirect('saas_business', slug=tenant.slug)
    if not pending.provider_order:
        try:
            billing.create_pending_signup_order(pending)
        except ValidationError as exc:
            messages.error(request, '; '.join(exc.messages))
            return redirect('saas_signup')
    purchase_agreement = active_purchase_agreement()
    return render(request, 'saas/pending_checkout.html', {
        'pending': pending,
        'key_id': settings.RAZORPAY_KEY_ID,
        'purchase_agreement': purchase_agreement,
        'cycle_label': _cycle_label(pending.billing_months),
    })


@require_POST
def pending_payment_verify(request, signup_id):
    pending = get_object_or_404(PendingSignup.objects.select_related('plan'), uuid=signup_id)
    if pending.status == 'paid':
        tenant = Tenant.objects.filter(slug=pending.username).select_related('owner').first()
        if tenant:
            if tenant.owner:
                login(request, tenant.owner, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, 'Payment verified. Your website is ready.')
            return redirect('saas_business', slug=tenant.slug)
        messages.success(request, 'Payment verified. Please sign in to continue.')
        return redirect('saas_login')
    if pending.status == 'failed':
        messages.error(request, 'This payment attempt failed. Please start checkout again.')
        return redirect('saas_signup')
    order_id = request.POST.get('razorpay_order_id', '')
    payment_id = request.POST.get('razorpay_payment_id', '')
    signature = request.POST.get('razorpay_signature', '')
    if request.POST.get('accepted_purchase_terms') != 'on':
        messages.error(request, 'Please read and accept the plan purchase terms to continue.')
        return redirect('saas_pending_checkout', signup_id=pending.uuid)
    if order_id != pending.provider_order:
        messages.error(request, 'This payment does not match the active checkout.')
        return redirect('saas_pending_checkout', signup_id=pending.uuid)
    try:
        billing.verify_signature(order_id, payment_id, signature)
        user, tenant = billing.settle_pending_signup(pending, payment_id)
        PurchaseAgreementAcceptance.objects.filter(pending_signup=pending, user__isnull=True).update(user=user, tenant=tenant)
        send_signup_email(user=user, tenant=tenant)
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        messages.success(request, 'Payment verified. Your website is ready.')
        return redirect('saas_business', slug=tenant.slug)
    except ValidationError as exc:
        messages.error(request, '; '.join(exc.messages))
        return redirect('saas_pending_checkout', signup_id=pending.uuid)


@login_required(login_url='saas_login')
def workspaces(request):
    memberships = request.user.memberships.filter(is_active=True, role__in=['owner', 'admin'], is_approved=True).select_related('tenant')
    return render(request, 'saas/workspaces.html', {'memberships': memberships})


def business_admin(view):
    @wraps(view)
    def wrapped(request, slug, *args, **kwargs):
        tenant = get_object_or_404(Tenant, slug=slug)
        if request.tenant is None:
            target = tenant.public_url.rstrip('/') + request.get_full_path()
            return redirect(target)
        if not request.user.is_authenticated:
            return redirect(f"{reverse('saas_login')}?next={quote(request.get_full_path())}")
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
    subscription = getattr(tenant, 'subscription', None)
    payments_enabled = bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET)
    payment_available = payments_enabled and (
        not subscription
        or not subscription.is_trial
        or subscription.expires_at <= timezone.now()
    )
    return render(request, 'saas/business.html', {
        'business': tenant, 'subscription': subscription,
        'listing_count': Property.objects.filter(tenant=tenant).count(),
        'pending_count': Property.objects.filter(tenant=tenant, is_active=False).count(),
        'member_count': tenant.memberships.filter(is_active=True).count(),
        'events': tenant.events.order_by('-created_at')[:8],
        'orders': latest_payment_history(tenant),
        'plans': Plan.objects.filter(is_active=True),
        'payments_enabled': payments_enabled,
        'payment_available': payment_available,
        'billing_cycles': (
            (1, '1 month'),
            (12, '1 year'),
            (24, '2 years'),
        ),
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
            if tenant.domains.filter(is_platform=False).count() >= 5:
                raise ValidationError('Maximum five domains per business.')
            Domain.objects.create(tenant=tenant, hostname=form.cleaned_data['hostname'])
            return redirect('saas_domains', slug=tenant.slug)
        except (ValidationError, IntegrityError) as exc:
            form.add_error(None, exc if isinstance(exc, ValidationError) else 'This domain is already registered.')
    return render(request, 'saas/domains.html', {'business': tenant, 'form': form, 'domains': tenant.domains.all(), 'target': settings.SAAS_DOMAIN_TARGET, 'server_ip': settings.SAAS_SERVER_IP})


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
        domain.provisioning_requested = True
        domain.last_attempt_at = None
        domain.save(update_fields=['is_verified', 'error', 'provisioning_requested', 'last_attempt_at'])
        messages.success(request, 'Ownership verified. Automatic HTTPS setup is queued. Keep your DNS pointed to our server.')
    except Exception:
        messages.error(request, 'TXT verification record is not available yet. Check the record and retry.')
    return redirect('saas_domains', slug=tenant.slug)


@business_admin
@require_POST
def checkout(request, tenant):
    plan = get_object_or_404(Plan, pk=request.POST.get('plan'), is_active=True)
    billing_months = _billing_months(request.POST.get('billing_months'))
    try:
        order = billing.create_order(tenant, plan, months=billing_months)
    except ValidationError as exc:
        messages.error(request, '; '.join(exc.messages))
        return redirect('saas_business', slug=tenant.slug)
    plan_discount = order.subtotal_amount * order.discount_percent // 100
    last_paid_credit = max(0, order.discount_amount - plan_discount)
    purchase_agreement = active_purchase_agreement()
    return render(request, 'saas/checkout.html', {
        'business': tenant,
        'order': order,
        'key_id': settings.RAZORPAY_KEY_ID,
        'purchase_agreement': purchase_agreement,
        'plan_discount_rupees': plan_discount / 100,
        'last_paid_credit_rupees': last_paid_credit / 100,
        'cycle_label': _cycle_label(order.billing_months),
    })


@business_admin
@require_POST
def payment_verify(request, tenant):
    order = get_object_or_404(BillingOrder, tenant=tenant, provider_order=request.POST.get('razorpay_order_id'))
    if request.POST.get('accepted_purchase_terms') != 'on':
        messages.error(request, 'Please read and accept the plan purchase terms to continue.')
        return redirect('dashboard_subscription')
    try:
        billing.verify_signature(order.provider_order, request.POST.get('razorpay_payment_id', ''), request.POST.get('razorpay_signature', ''))
        if not order.purchase_agreement_acceptances.exists():
            record_purchase_agreement_acceptance(
                user=request.user,
                tenant=tenant,
                order=order,
                agreement=active_purchase_agreement(),
                request=request,
            )
        billing.settle(order, request.POST.get('razorpay_payment_id', ''))
        messages.success(request, 'Payment verified. Your subscription is active.')
    except ValidationError as exc:
        messages.error(request, '; '.join(exc.messages))
    return redirect('saas_business', slug=tenant.slug)


@business_admin
def invoice(request, tenant, order_uuid):
    order = get_object_or_404(BillingOrder.objects.select_related('plan', 'tenant', 'tenant__owner'), uuid=order_uuid, tenant=tenant, status='paid')
    return render(request, 'saas/invoice.html', {
        'business': tenant,
        'order': order,
        'billing_setting': billing.BillingSetting.current(),
        'cycle_label': _cycle_label(order.billing_months),
    })


@business_admin
def invoice_download(request, tenant, order_uuid):
    order = get_object_or_404(BillingOrder.objects.select_related('plan', 'tenant', 'tenant__owner'), uuid=order_uuid, tenant=tenant, status='paid')
    pdf_bytes, invoice_no = _invoice_pdf(order, tenant)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{invoice_no}.pdf"'
    return response


def whatsapp_invoice_pdf(request, token):
    try:
        payload = signing.loads(token, salt=WHATSAPP_INVOICE_SIGNER_SALT, max_age=60 * 60 * 24 * 30)
    except signing.BadSignature:
        return HttpResponse(status=404)
    order = get_object_or_404(
        BillingOrder.objects.select_related('plan', 'tenant', 'tenant__owner'),
        pk=payload.get('order_id'),
        status='paid',
    )
    pdf_bytes, invoice_no = _invoice_pdf(order, order.tenant)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{invoice_no}.pdf"'
    return response


@csrf_exempt
@require_POST
def webhook(request):
    try:
        event = billing.process_webhook(
            request.body,
            request.headers.get('X-Razorpay-Signature', ''),
            request.headers.get('X-Razorpay-Event-Id', ''),
        )
    except ValidationError:
        return HttpResponse(status=400)
    return JsonResponse({'processed': bool(event.processed_at), 'event_id': event.event_id})

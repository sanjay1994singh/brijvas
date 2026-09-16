from django.utils.http import url_has_allowed_host_and_scheme
from django.db import transaction
from saas.models import Membership
from saas.scoping import scoped
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q

from .forms import RegisterForm, ProfileForm
from .username_utils import suggest_usernames, username_exists, validate_username
from properties.models import Property
from enquiries.models import Enquiry
from django.conf import settings
from django.contrib.auth.views import PasswordResetView
from django.contrib.auth import get_user_model
from .phone_utils import indian_mobile_last10, normalize_indian_mobile
from core.images import optimize_uploaded_image


def login_candidates(identifier):
    identifier = (identifier or "").strip()
    if not identifier:
        return []
    User = get_user_model()
    users = list(User.objects.filter(Q(username__iexact=identifier) | Q(email__iexact=identifier)).order_by('id'))
    digits = indian_mobile_last10(identifier)
    if len(digits) == 10:
        users.extend(User.objects.filter(phone__endswith=digits).order_by('id'))
    unique = {}
    for user in users:
        unique[user.pk] = user
    return list(unique.values())


def resolve_login_username(identifier, tenant=None):
    identifier = (identifier or "").strip()
    if not identifier:
        return identifier
    matches = login_candidates(identifier)
    if tenant and matches:
        matches = [
            user for user in matches
            if Membership.objects.filter(tenant=tenant, user=user, is_active=True).exists()
        ]
    if len(matches) == 1:
        return matches[0].username
    return identifier


class ConfiguredPasswordResetView(PasswordResetView):
    template_name = 'accounts/password_reset.html'
    email_template_name = 'accounts/password_reset_email.txt'
    subject_template_name = 'accounts/password_reset_subject.txt'

    def dispatch(self, request, *args, **kwargs):
        if settings.EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend' and not settings.EMAIL_HOST:
            return render(request, self.template_name, {'email_unavailable': True}, status=503)
        return super().dispatch(request, *args, **kwargs)


def register(request):
    if not request.tenant:
        return redirect('saas_signup')
    if request.user.is_authenticated:
        return redirect('dashboard' if request.tenant else 'saas_workspaces')

    if request.method == "POST":

        form = RegisterForm(request.POST)

        if form.is_valid():
            with transaction.atomic():
                user = form.save()
                role = {'owner': 'seller', 'agent': 'agent'}.get(user.user_type, 'buyer')
                Membership.objects.create(tenant=request.tenant, user=user, role=role, is_approved=(role == 'buyer'))

            login(
                request,
                user,
                backend="django.contrib.auth.backends.ModelBackend"
            )

            messages.success(
                request,
                "Account created successfully."
            )

            return redirect("dashboard")

    else:

        form = RegisterForm()

    context = {
        "form": form
    }

    return render(
        request,
        "accounts/register.html",
        context
    )


def check_username(request):
    username = (request.GET.get("username") or "").strip()

    if not username:
        return JsonResponse(
            {
                "available": False,
                "message": "Please enter a username.",
                "suggestions": [],
            }
        )

    if not validate_username(username):
        return JsonResponse(
            {
                "available": False,
                "message": "Use only letters, numbers and @/./+/-/_.",
                "suggestions": suggest_usernames(username),
            }
        )

    available = not username_exists(username)

    return JsonResponse(
        {
            "available": available,
            "message": (
                "Username is available."
                if available
                else "Username is already taken."
            ),
            "suggestions": [] if available else suggest_usernames(username),
        }
    )


def user_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard' if request.tenant else 'saas_workspaces')

    if request.method == "POST":

        selected_username = (request.POST.get("account_username") or "").strip()
        identifier = request.POST.get("username")
        candidates = login_candidates(identifier)
        if request.tenant and candidates:
            candidates = [
                user for user in candidates
                if Membership.objects.filter(tenant=request.tenant, user=user, is_active=True).exists()
            ]
        if selected_username and candidates and not any(user.username == selected_username for user in candidates):
            selected_username = ""
        if not selected_username and len(candidates) > 1:
            return render(
                request,
                "accounts/login.html" if request.tenant else "saas/login.html",
                {"login_identifier": identifier, "login_accounts": candidates},
            )
        username = selected_username
        if not username and len(candidates) == 1:
            username = candidates[0].username
        if not username:
            username = resolve_login_username(identifier, request.tenant)

        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user and (not request.tenant or Membership.objects.filter(tenant=request.tenant, user=user, is_active=True).exists()):

            login(request, user)

            next_url = request.GET.get("next")

            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
                return redirect(next_url)

            return redirect('dashboard' if request.tenant else 'saas_workspaces')

        messages.error(
            request,
            "Invalid username or password."
        )

    return render(
        request,
        "accounts/login.html" if request.tenant else "saas/login.html"
    )


@login_required
def user_logout(request):
    logout(request)

    messages.success(
        request,
        "Logged out successfully."
    )

    return redirect("login")


# @login_required
# def profile(request):
#     if request.method == "POST":
#
#         form = ProfileForm(
#             request.POST,
#             request.FILES,
#             instance=request.user
#         )
#
#         if form.is_valid():
#             form.save()
#
#             messages.success(
#                 request,
#                 "Profile updated successfully."
#             )
#
#             return redirect("profile")
#
#     else:
#
#         form = ProfileForm(
#             instance=request.user
#         )
#
#     context = {
#         "form": form
#     }
#
#     return render(
#         request,
#         "accounts/profile.html",
#         context
#     )
@login_required
def profile(request):
    property_count = scoped(Property, request.tenant).filter(
        user=request.user
    ).count()

    enquiry_count = scoped(Enquiry, request.tenant).filter(
        property__user=request.user
    ).count()

    if request.method == "POST":

        form = ProfileForm(
            request.POST,
            request.FILES,
            instance=request.user
        )

        if form.is_valid():
            user = form.save()
            if user.profile_image:
                optimize_uploaded_image(
                    user.profile_image,
                    max_size=(600, 600),
                    target_kb=300,
                    quality=88,
                    min_quality=76,
                )
            messages.success(
                request,
                "Profile updated successfully."
            )
            return redirect("profile")

    else:

        form = ProfileForm(
            instance=request.user
        )

    return render(
        request,
        "accounts/profile.html",
        {
            "form": form,
            "property_count": property_count,
            "enquiry_count": enquiry_count,
        }
    )

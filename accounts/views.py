from django.utils.http import url_has_allowed_host_and_scheme
from django.db import transaction
from saas.models import Membership
from saas.scoping import scoped
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from .forms import RegisterForm, ProfileForm
from .username_utils import suggest_usernames, username_exists, validate_username
from properties.models import Property
from enquiries.models import Enquiry
from django.conf import settings
from django.contrib.auth.views import PasswordResetView


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

        username = request.POST.get("username")

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
            form.save()
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

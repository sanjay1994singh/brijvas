from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from .forms import RegisterForm, ProfileForm
from .username_utils import suggest_usernames, username_exists, validate_username
from properties.models import Property
from enquiries.models import Enquiry


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":

        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save()

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
        return redirect("dashboard")

    if request.method == "POST":

        username = request.POST.get("username")

        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user:

            login(request, user)

            next_url = request.GET.get("next")

            if next_url:
                return redirect(next_url)

            return redirect("dashboard")

        messages.error(
            request,
            "Invalid username or password."
        )

    return render(
        request,
        "accounts/login.html"
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
    property_count = Property.objects.filter(
        user=request.user
    ).count()

    enquiry_count = Enquiry.objects.filter(
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

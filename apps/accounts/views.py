from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _

from .forms import OnboardingStep1Form, OnboardingStep2Form, ProfileForm
from .models import UserProfile


def home_view(request):
    """Render the home page."""
    return render(request, "pages/home.html")


@login_required
def profile_view(request):
    """Render and handle the user profile page."""
    profile, _created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, _("Profile updated successfully."))
    else:
        form = ProfileForm(instance=profile)

    return render(request, "accounts/profile.html", {"form": form, "profile": profile})


@login_required
def onboarding_view(request):
    """Render the onboarding shell with step 1 loaded."""
    profile, _created = UserProfile.objects.get_or_create(user=request.user)
    if profile.onboarding_completed:
        return redirect("portfolio:list")
    form = OnboardingStep1Form(instance=profile)
    return render(
        request,
        "accounts/onboarding.html",
        {"step": 1, "form": form, "profile": profile},
    )


@login_required
def onboarding_step(request, step):
    """Handle each onboarding step via HTMX partial swap."""
    profile, _created = UserProfile.objects.get_or_create(user=request.user)

    if step == 1:
        if request.method == "POST":
            form = OnboardingStep1Form(request.POST, instance=profile)
            if form.is_valid():
                form.save()
                form2 = OnboardingStep2Form(instance=profile)
                return render(
                    request,
                    "accounts/partials/onboarding_step_2.html",
                    {"step": 2, "form": form2, "profile": profile},
                )
        else:
            form = OnboardingStep1Form(instance=profile)
        return render(
            request,
            "accounts/partials/onboarding_step_1.html",
            {"step": 1, "form": form, "profile": profile},
        )

    if step == 2:
        if request.method == "POST":
            form = OnboardingStep2Form(request.POST, instance=profile)
            if form.is_valid():
                form.save()
                return render(
                    request,
                    "accounts/partials/onboarding_step_3.html",
                    {"step": 3, "profile": profile},
                )
        else:
            form = OnboardingStep2Form(instance=profile)
        return render(
            request,
            "accounts/partials/onboarding_step_2.html",
            {"step": 2, "form": form, "profile": profile},
        )

    if step == 3:
        profile.onboarding_completed = True
        profile.save()
        return redirect("portfolio:list")

    return redirect("accounts:onboarding")

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _

from .forms import ProfileForm
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

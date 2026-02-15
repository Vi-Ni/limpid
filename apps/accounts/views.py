from django.contrib.auth.decorators import login_required
from django.shortcuts import render


def home_view(request):
    """Render the home page."""
    return render(request, "pages/home.html")


@login_required
def profile_view(request):
    """Render the user profile page."""
    return render(request, "accounts/profile.html")

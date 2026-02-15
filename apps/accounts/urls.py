from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("profile/", views.profile_view, name="profile"),
    path("onboarding/", views.onboarding_view, name="onboarding"),
    path("onboarding/step/<int:step>/", views.onboarding_step, name="onboarding_step"),
]

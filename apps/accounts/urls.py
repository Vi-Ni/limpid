from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("profile/", views.profile_view, name="profile"),
    path("onboarding/", views.onboarding_view, name="onboarding"),
    path("onboarding/step/<int:step>/", views.onboarding_step, name="onboarding_step"),
    path("risk-quiz/", views.risk_quiz_view, name="risk_quiz"),
    path("risk-quiz/step/<int:step>/", views.risk_quiz_step, name="risk_quiz_step"),
    path("risk-quiz/results/", views.risk_quiz_results, name="risk_quiz_results"),
]

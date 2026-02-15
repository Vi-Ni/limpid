from django.urls import path

from . import views

app_name = "scenarios"

urlpatterns = [
    path("", views.scenario_lab, name="lab"),
]

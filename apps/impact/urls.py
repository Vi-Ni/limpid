from django.urls import path

from . import views

app_name = "impact"

urlpatterns = [
    path("", views.directory, name="directory"),
]

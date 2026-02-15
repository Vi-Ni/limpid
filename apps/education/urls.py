from django.urls import path

from . import views

app_name = "education"

urlpatterns = [
    path("", views.learning_path, name="path"),
]

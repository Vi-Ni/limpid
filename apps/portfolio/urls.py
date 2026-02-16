from django.urls import path

from . import views

app_name = "portfolio"

urlpatterns = [
    path("", views.portfolio_list, name="list"),
    path("<int:pk>/", views.portfolio_detail, name="detail"),
]

from django.urls import path

from apps.accounts.views import home_view, styleguide_view
from apps.portfolio.views import dashboard_view

urlpatterns = [
    path("", home_view, name="home"),
    path("dashboard/", dashboard_view, name="dashboard"),
    path("styleguide/", styleguide_view, name="styleguide"),
]

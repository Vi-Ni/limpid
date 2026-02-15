from django.urls import path

from apps.accounts.views import home_view, styleguide_view

urlpatterns = [
    path("", home_view, name="home"),
    path("styleguide/", styleguide_view, name="styleguide"),
]

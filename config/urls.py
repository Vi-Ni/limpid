"""Root URL configuration."""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("portfolio/", include("apps.portfolio.urls")),
    path("market/", include("apps.market_data.urls")),
    path("transparency/", include("apps.transparency.urls")),
    path("learn/", include("apps.education.urls")),
    path("scenarios/", include("apps.scenarios.urls")),
    path("impact/", include("apps.impact.urls")),
    path("", include("apps.accounts.urls_home")),
]

if settings.DEBUG:
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls")),
        path("__reload__/", include("django_browser_reload.urls")),
    ]

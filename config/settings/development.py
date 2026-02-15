"""Development settings."""

from .base import *  # noqa: F403, F401
from .base import INSTALLED_APPS, MIDDLEWARE, env

DEBUG = True
ALLOWED_HOSTS = ["*"]

# django-debug-toolbar
INSTALLED_APPS += [
    "debug_toolbar",
    "django_browser_reload",
]
MIDDLEWARE += [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "django_browser_reload.middleware.BrowserReloadMiddleware",
]
INTERNAL_IPS = ["127.0.0.1"]

# Vite dev mode
# Use simple static files storage in dev (no WhiteNoise compression)
STORAGES = {
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# Vite dev mode — assets served at http://localhost:5173/static/src/main.js
DJANGO_VITE = {
    "default": {
        "dev_mode": True,
        "dev_server_host": "localhost",
        "dev_server_port": 5173,
        "static_url_prefix": "",
    }
}

# Email
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Use default secret key in dev
SECRET_KEY = env("SECRET_KEY", default="django-insecure-dev-key-change-in-production")

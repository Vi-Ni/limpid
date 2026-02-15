"""Test settings for fast test execution."""

from .base import *  # noqa: F403, F401

DEBUG = False
SECRET_KEY = "test-secret-key-not-for-production"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Disable Vite manifest check in tests
DJANGO_VITE = {
    "default": {
        "dev_mode": True,
        "dev_server_host": "localhost",
        "dev_server_port": 5173,
    }
}

SILENCED_SYSTEM_CHECKS = ["django_vite.W001"]

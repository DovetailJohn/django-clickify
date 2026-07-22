import os
import tempfile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = "fake-key"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": os.path.join(BASE_DIR, "django_cache"),
    }
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "rest_framework",
    "clickify",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "clickify.drf_exceptions.custom_exception_handler"
}


MIDDLEWARE = [
    "clickify.middleware.IPFilterMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",  # Required!
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"


MEDIA_ROOT = os.path.join(tempfile.gettempdir(), "clickify_tests")

ROOT_URLCONF = "tests.urls"
RATELIMIT_VIEW = "django_ratelimit.views.ratelimited"

USE_TZ = True

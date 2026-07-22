from django.contrib import admin
from django.urls import include, path

# Temporary urls for testing
urlpatterns = [
    path("admin/", admin.site.urls),
    path("track/", include("clickify.urls", namespace="clickify")),
    path("api/track/", include("clickify.drf_urls", namespace="clickify-drf")),
]

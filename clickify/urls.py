from django.urls import path

from .views import track_click

app_name = "clickify"

urlpatterns = [
    path("<slug:slug>", track_click, name="track_click"),
    path("<slug:slug>/", track_click),
]

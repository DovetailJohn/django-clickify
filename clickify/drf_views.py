from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.module_loading import import_string
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .decorators import conditional_ratelimit
from .models import TrackedLink
from .utils import build_redirect_url, create_click_log


@method_decorator(conditional_ratelimit, name="post")
class TrackClickAPIView(APIView):
    """An API View to track a click for a TrackedLink."""

    def get_permissions(self):
        """Return permission instances for this view.

        This is called at runtime, so it will pick up @override_settings changes.
        """
        permission_classes = getattr(
            settings, "CLICKIFY_PERMISSION_CLASSES", [AllowAny]
        )

        # Handle both class objects and string paths
        permissions = []
        for perm_class in permission_classes:
            if isinstance(perm_class, str):
                # Import the class from string path
                perm_class = import_string(perm_class)
            permissions.append(perm_class())

        return permissions

    def post(self, request, slug, format=None):
        """Tracks a click for the given slug."""
        target = get_object_or_404(TrackedLink, slug=slug)
        redirect_url, utm_params = build_redirect_url(target, request._request)
        create_click_log(target=target, request=request._request, utm_params=utm_params)
        return Response(
            {"message": "Click tracked successfully", "target_url": redirect_url},
            status=status.HTTP_200_OK,
        )

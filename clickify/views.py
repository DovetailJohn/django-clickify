from urllib.parse import urlparse, parse_qs

from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404

from .decorators import conditional_ratelimit
from .models import TrackedLink
from .utils import create_click_log, build_redirect_url


@conditional_ratelimit
def track_click(request, slug):
    """Track a click for a TrackedLink and redirect - using utility function."""
    target = get_object_or_404(TrackedLink, slug=slug)
    redirect_url = build_redirect_url(target, request)
    final_qs = parse_qs(urlparse(redirect_url).query, keep_blank_values=True)
    utm_log = {k: v[0] for k, v in final_qs.items() if k.startswith("utm_")}
    create_click_log(target=target, request=request, utm_params=utm_log)
    return HttpResponseRedirect(redirect_url)

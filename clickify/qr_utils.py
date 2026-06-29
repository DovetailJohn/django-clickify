# QR Utility Functions

from __future__ import annotations

import base64
import io
from copy import deepcopy
from functools import lru_cache
from typing import TYPE_CHECKING, BinaryIO

from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.exceptions import ImproperlyConfigured
from django.utils.html import format_html
from django.utils.module_loading import import_string

if TYPE_CHECKING:
    from .models import TrackedLink


DEFAULT_SEGNO_CONFIG = {
    "MAKE_KWARGS": {"error": "h"},
    "SAVE_KWARGS": {"kind": "png", "scale": 10, "border": 1},
}

SEGNO_CONFIG_KEYS = {"MAKE_KWARGS", "SAVE_KWARGS"}

def is_qr_enabled() -> bool:
    """Return True if QR code generation is configured."""
    return bool(getattr(settings, "CLICKIFY_QR_BASE_URI", ""))

def get_qr_url(obj: TrackedLink) -> str:
    """Build the public-facing tracking URL for a TrackedLink."""
    base = getattr(settings, "CLICKIFY_QR_BASE_URI", "")
    if not base:
        return ""
    try:
        url = base.format(slug=obj.slug)
    except KeyError as ex:
        raise ImproperlyConfigured(
            f"Invalid placeholder '{ex.args[0]}' in CLICKIFY_QR_BASE_URI"
        ) from ex

    return url

def get_qr_code_generator():
    """Return a callable implementing the QR generation API."""
    path_or_callable = getattr(settings, "CLICKIFY_QR_GENERATOR", "clickify.qr_utils.segno_qr_generator")

    if callable(path_or_callable):
        return path_or_callable

    # assume dotted path string
    return import_string(path_or_callable)

@lru_cache(maxsize=1)
def get_segno_config():
    """Load and merge CLICKIFY_QR_SEGNO_CONFIG with defaults."""
    user_config = getattr(settings, "CLICKIFY_QR_SEGNO_CONFIG", {})

    merged = deepcopy(DEFAULT_SEGNO_CONFIG)

    if not isinstance(user_config, dict):
        raise ImproperlyConfigured("CLICKIFY_QR_SEGNO_CONFIG must be a dictionary.")

    for key, value in user_config.items():
        if key not in SEGNO_CONFIG_KEYS:
            raise ImproperlyConfigured(
                f"Invalid key '{key}' in CLICKIFY_QR_SEGNO_CONFIG. "
                f"Allowed keys: {', '.join(SEGNO_CONFIG_KEYS)}."
            )
        if not isinstance(value, dict):
            raise ImproperlyConfigured(f"{key} must be a dictionary.")

        merged[key].update(value)

    return merged

def insert_image(qr_buffer: BinaryIO, logo_path: str) -> bytes:
    """Embed a logo image into the center of a QR code PNG buffer."""
    try:
        from PIL import Image
    except ImportError as ex:
        raise ImproperlyConfigured(
            "Pillow is required for QR Image Insert. "
            "Install it or override CLICKIFY_QR_GENERATOR."
        ) from ex

    try:

        # 1. Composite logo using Pillow
        #    (This adds a dependency on Pillow, but keeps everything else minimal)
        qr_img = Image.open(qr_buffer).convert("RGBA")

        logo_img = Image.open(logo_path).convert("RGBA")

        # 2. Resize logo to be a fraction of the QR size
        qr_width, qr_height = qr_img.size
        logo_scale = getattr(settings, "CLICKIFY_QR_LOGO_SCALE", 0.35)
        logo_size = int(qr_width * logo_scale)
        logo_img.thumbnail((logo_size, logo_size), Image.LANCZOS)

        # 3. Compute centered position
        logo_width, logo_height = logo_img.size
        pos = (
            (qr_width - logo_width) // 2,
            (qr_height - logo_height) // 2,
        )

        # 4. Paste logo with alpha (if any)
        qr_img.paste(logo_img, pos, logo_img)

        # 5. Save final composite as PNG in memory
        out_buffer = io.BytesIO()
        qr_img.save(out_buffer, format="PNG")
        return out_buffer.getvalue()
    except Exception as ex:
        raise RuntimeError("QR code image add failed") from ex


def segno_qr_image(url: str) -> bytes:
    """Generate a QR code PNG for the given URL using segno.

    Optionally embed a logo image at the center (if CLICKIFY_QR_LOGO_PATH is in settings).

    Returns raw PNG bytes.
    """
    try:
        import segno
    except ImportError as ex:
        raise ImproperlyConfigured(
            "segno is required for QR code generation. "
            "Install it or override CLICKIFY_QR_GENERATOR."
        ) from ex

    try:
        if not url:
            raise ValueError("URL is required to generate a QR code")

        segno_config = get_segno_config()

        # 1. Create QR code with segno (no logo yet)
        qr = segno.make(url, **segno_config['MAKE_KWARGS'])
        qr_buffer = io.BytesIO()
        qr.save(qr_buffer, **segno_config['SAVE_KWARGS'])
        qr_buffer.seek(0)

        logo_setting = getattr(settings, "CLICKIFY_QR_LOGO_PATH", None)

        # 2. If no logo, we can just return the segno-generated PNG bytes
        if not logo_setting:
            return qr_buffer.getvalue()

        logo_path = finders.find(logo_setting) if logo_setting else None
        if not logo_path:
            raise ImproperlyConfigured(
                f"CLICKIFY_QR_LOGO_PATH='{logo_setting}' could not be found via staticfiles."
            )

        # 3. Call insert_logo to add the logo to the PNG buffer.
        return insert_image(qr_buffer, logo_path)
    except Exception as ex:
        raise RuntimeError("QR code generation failed") from ex


def segno_qr_generator(tracked_link: TrackedLink) -> str:
    """Returns the html string with the img tag for displaying a segno generated QR Code

    :param tracked_link: Description
    :type tracked_link: TrackedLink
    """
    url = get_qr_url(tracked_link)
    if not url:
        return "QR code not available (base URI not configured or generation failed)."

    png_bytes = segno_qr_image(url)
    b64 = base64.b64encode(png_bytes).decode("ascii")
    qr_image = f"data:image/png;base64,{b64}"
    return format_html(
        """
        <div id="copy-tracked-link-url" style="cursor: pointer; padding: 4px; background: #f7f7f7; border: 1px solid #ddd; display: inline-block;">
            {url}
        </div>

        <script>
        (function() {{
            const div = document.getElementById("copy-tracked-link-url");
            if (div) {{
                div.addEventListener("click", function() {{
                    navigator.clipboard.writeText(div.textContent.trim()).then(function() {{
                        div.style.backgroundColor = "#dff0d8";  // light green success indicator
                        setTimeout(() => {{
                            div.style.backgroundColor = "#f7f7f7";
                        }}, 800);
                    }});
                }});
            }}
        }})();
        </script>

        <div style="margin-top: 8px;">
            <img src="{qr_image}" alt="QR code for '{url}'" style="max-width: 200px; height: auto;" />
        </div>

        <div style="margin-top: 6px;">
            <a href="{qr_image}" download="{slug}-qr.png">Download QR code</a>
        </div>
        """,
        url=url,
        qr_image=qr_image,
        slug=tracked_link.slug,
    )

def get_qr_code_html(tracked_link: TrackedLink):
    """Convenience wrapper around the configured CLICKIFY_QR_GENERATOR.

    Returns whatever the generator returns (by default, an <img> tag with a data URI src).
    """
    return get_qr_code_generator()(tracked_link)

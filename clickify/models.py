import re
import uuid

from django.core.exceptions import ValidationError
from django.db import models

_PARAM_NAME_RE = re.compile(r"^[A-Za-z0-9_\-\.]+$")


def validate_forward_params(value):
    """Validate a comma-separated list of query parameter names.

    Each token must be a bare param name: no '=', no spaces, no 'utm_' prefix.
    """
    if not value:
        return
    errors = []
    for raw in value.split(","):
        token = raw.strip()
        if not token:
            continue
        if "=" in token:
            errors.append(f"'{token}': use a parameter name only, not 'name=value'.")
        elif token.lower().startswith("utm_"):
            errors.append(f"'{token}': UTM parameters are managed via the UTM fields above.")
        elif not _PARAM_NAME_RE.match(token):
            errors.append(f"'{token}': only letters, numbers, hyphens, underscores and dots are allowed.")
    if errors:
        raise ValidationError(errors)


class UtmSource(models.Model):
    """Admin-managed lookup table of allowed utm_source values."""

    value = models.CharField(
        max_length=255, unique=True,
        help_text=(
            "The utm_source value sent to analytics. "
            "e.g. 'email', 'google', 'facebook', 'newsletter'. "
            "Use lowercase with no spaces — this is what appears in your reports."
        ),
    )
    label = models.CharField(
        max_length=255, blank=True,
        help_text=(
            "Optional human-readable description shown in the admin dropdown. "
            "e.g. 'Email Newsletter', 'Google Ads'. Leave blank to use the value."
        ),
    )

    def __str__(self):
        return f"{self.value} — {self.label}" if self.label else self.value

    class Meta:
        """Model metadata for UtmSource."""

        ordering = ["value"]
        verbose_name = "UTM Source"
        verbose_name_plural = "UTM Sources"


class UtmMedium(models.Model):
    """Admin-managed lookup table of allowed utm_medium values."""

    value = models.CharField(
        max_length=255, unique=True,
        help_text=(
            "The utm_medium value sent to analytics. "
            "e.g. 'email', 'cpc', 'social', 'organic', 'referral'. "
            "Use lowercase with no spaces — this is what appears in your reports."
        ),
    )
    label = models.CharField(
        max_length=255, blank=True,
        help_text=(
            "Optional human-readable description shown in the admin dropdown. "
            "e.g. 'Email Campaign', 'Paid Search'. Leave blank to use the value."
        ),
    )

    def __str__(self):
        return f"{self.value} — {self.label}" if self.label else self.value

    class Meta:
        """Model metadata for UtmMedium."""

        ordering = ["value"]
        verbose_name = "UTM Medium"
        verbose_name_plural = "UTM Mediums"


class TrackedLink(models.Model):
    """Represents a link that can be tracked.

    This model decouples the link from its actual URL,
      allowing the URL to change without losing the click history.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=255,
        help_text="A user-friendly name for tracked link, e.g., Monthly Report PDF",
    )
    slug = models.SlugField(
        max_length=255,
        unique=True,
        help_text="A unique slug for the URL. E.g., 'monthly-report-pdf' ",
    )
    target_url = models.URLField(
        max_length=2048,
        help_text="The actual URL to the destination (e.g., on S3, a blog post, an affiliate link, etc.) - Not mandatory",
        blank=True, null=True
    )
    utm_source = models.ForeignKey(
        UtmSource, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="tracked_links",
        help_text=(
            "Identifies the traffic origin for this link. "
            "e.g. 'email' for a newsletter, 'google' for a Google Ad. "
            "Manage available options in the UTM Sources section."
        ),
    )
    utm_medium = models.ForeignKey(
        UtmMedium, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="tracked_links",
        help_text=(
            "Identifies the marketing channel type for this link. "
            "e.g. 'email' for email campaigns, 'cpc' for paid search. "
            "Manage available options in the UTM Mediums section."
        ),
    )
    utm_campaign = models.CharField(
        max_length=255, blank=True,
        help_text=(
            "The specific campaign this link belongs to. "
            "e.g. 'q3-newsletter-2026', 'spring-sale', 'product-launch'. "
            "Use lowercase with hyphens — no spaces. Leave blank if not part of a campaign."
        ),
    )
    utm_content = models.CharField(
        max_length=255, blank=True,
        help_text=(
            "Identifies this specific link within a campaign. "
            "e.g. 'header-cta', 'footer-button', 'sidebar-image'. "
            "Use this to distinguish multiple links in the same email or page."
        ),
    )
    utm_term = models.CharField(
        max_length=255, blank=True,
        help_text=(
            "The paid search keyword that triggered this ad. "
            "e.g. 'running+shoes'. Leave blank for non-paid-search links."
        ),
    )
    utm_override = models.BooleanField(
        default=False,
        help_text=(
            "Controls what happens when a visitor arrives with UTM parameters already "
            "in their click URL (e.g. from a social share or forwarded link). "
            "Checked: this link's stored UTM values always win — incoming params are replaced. "
            "Unchecked: incoming params take precedence; stored values fill any gaps."
        ),
    )
    forward_params = models.CharField(
        max_length=1024, blank=True,
        validators=[validate_forward_params],
        help_text=(
            "Comma-separated list of non-UTM query parameter names to forward from "
            "the visitor's click URL to the destination. "
            "e.g. 'name, ref_id, campaign_token'. "
            "UTM parameters are always handled separately via the UTM fields above. "
            "Leave blank to forward no extra parameters (recommended for public links)."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ClickLog(models.Model):
    """Logs a single click event for a TrackedLink."""

    target = models.ForeignKey(
        TrackedLink, on_delete=models.CASCADE, related_name="clicks"
    )
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    ref = models.TextField(default="", blank=True, null=True)
    utm_source = models.CharField(max_length=255, blank=True, null=True)
    utm_medium = models.CharField(max_length=255, blank=True, null=True)
    utm_campaign = models.CharField(max_length=255, blank=True, null=True)
    utm_content = models.CharField(max_length=255, blank=True, null=True)
    utm_term = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Click on {self.target.name} at {self.timestamp}"

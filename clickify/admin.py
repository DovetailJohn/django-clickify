from django.contrib import admin, messages
from django.utils.html import format_html

from .models import ClickLog, TrackedLink, UtmSource, UtmMedium

from .qr_utils import is_qr_enabled, get_qr_code_html
from .utils import get_geolocation


@admin.register(UtmSource)
class UtmSourceAdmin(admin.ModelAdmin):
    list_display = ("value", "label")
    search_fields = ("value", "label")


@admin.register(UtmMedium)
class UtmMediumAdmin(admin.ModelAdmin):
    list_display = ("value", "label")
    search_fields = ("value", "label")


@admin.register(TrackedLink)
class TrackedLinkAdmin(admin.ModelAdmin):
    """Admin view for TrackedLink."""

    list_display = ("name", "slug", "target_url", "created_at")
    search_fields = ("name", "slug", "target_url")
    prepopulated_fields = {"slug": ("name",)}
    list_filter = ("utm_source", "utm_medium", "created_at")
    autocomplete_fields = ["utm_source", "utm_medium"]

    fieldsets = (
        (None, {
            "fields": ("name", "slug", "target_url"),
        }),
        ("UTM Parameters", {
            "fields": (
                "utm_source", "utm_medium",
                "utm_campaign", "utm_content", "utm_term",
                "utm_override", "forward_params",
            ),
            "description": (
                "All UTM fields are optional. Select a source and medium from the "
                "managed lists (use + to add a new one). Campaign, content, and term "
                "are free-text — use lowercase with hyphens, no spaces."
            ),
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        """
        Add qr_preview as readonly, but only on the change view (obj != None).
        """
        ro = list(super().get_readonly_fields(request, obj))

        if is_qr_enabled() and obj is not None:
            ro.append("qr_preview")
        return ro

    @admin.display(description="QR Code")
    def qr_preview(self, obj):
        """
        Render an <img> tag using the configured QR Generation function.
        """
        try:

            if not obj:
                return "Save the object first to see a QR code."

            return get_qr_code_html(obj)

        except Exception as e:
            return format_html('<span>{}</span>', e)


@admin.register(ClickLog)
class ClickLogAdmin(admin.ModelAdmin):
    """Admin view for ClickLog."""

    list_display = ("target", "ip_address", "country", "city",
                    "utm_source", "utm_campaign", "timestamp")
    search_fields = ("target__name", "ip_address", "country", "city",
                     "utm_source", "utm_medium", "utm_campaign", "utm_content")
    list_filter = ("target", "country", "utm_source", "utm_medium",
                   "utm_campaign", "timestamp")
    readonly_fields = [field.name for field in ClickLog._meta.fields]

    actions = ["update_geolocation"]

    def has_add_permission(self, request):
        """Prevent adding new ClickLogs from the admin."""
        return False

    def update_geolocation(self, request, queryset):
        """
        Admin action to update geolocation (country, city) for selected ClickLogs.
        """
        updated = 0

        for log in queryset:
            if log.ip_address:
                try:
                    country, city = get_geolocation(log.ip_address, force=True)
                    log.country = country
                    log.city = city
                    log.save(update_fields=["country", "city"])
                    updated += 1
                except Exception as exc:
                    # If one entry fails, keep going
                    self.message_user(
                        request,
                        f"Error updating IP {log.ip_address}: {exc}",
                        level=messages.WARNING,
                    )

        self.message_user(
            request,
            f"Updated geolocation for {updated} log(s).",
            level=messages.SUCCESS,
        )

    update_geolocation.short_description = "Update geolocation for selected logs"

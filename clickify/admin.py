from django.contrib import admin, messages
from django.utils.html import format_html

from .models import ClickLog, TrackedLink

from .qr_utils import is_qr_enabled, get_qr_code_html
from .utils import get_geolocation


@admin.register(TrackedLink)
class TrackedLinkAdmin(admin.ModelAdmin):
    """Admin view for TrackedLink."""

    list_display = ("name", "slug", "target_url", "created_at")
    search_fields = ("name", "slug", "target_url")
    prepopulated_fields = {"slug": ("name",)}
    list_filter = ("created_at",)

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

    list_display = ("target", "ip_address", "country", "city", "timestamp")
    search_fields = ("target__name", "ip_address", "country", "city")
    list_filter = ("target", "country", "timestamp")
    #readonly_fields = [field.name for field in ClickLog._meta.fields]

    actions = ["update_geolocation"]

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

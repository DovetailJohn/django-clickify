from django.contrib import admin
from django.utils.html import format_html

from .models import ClickLog, TrackedLink

from .qr_utils import is_qr_enabled, get_qr_code_html

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
    readonly_fields = [field.name for field in ClickLog._meta.fields]

    def has_add_permission(self, request):
        """Prevent adding new ClickLogs from the admin."""
        return False

    def has_delete_permission(self, request, obj=...):
        """Prevent deleting ClickLogs from the admin."""
        return False

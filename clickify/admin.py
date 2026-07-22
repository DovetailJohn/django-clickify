import datetime

from django.contrib import admin, messages
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.template.response import TemplateResponse
from django.utils.html import format_html

from .models import ClickLog, ClickReport, TrackedLink, UtmMedium, UtmSource
from .qr_utils import get_qr_code_html, is_qr_enabled
from .utils import get_geolocation


@admin.register(UtmSource)
class UtmSourceAdmin(admin.ModelAdmin):
    """Admin for the UTM source lookup table."""

    list_display = ("value", "label")
    search_fields = ("value", "label")


@admin.register(UtmMedium)
class UtmMediumAdmin(admin.ModelAdmin):
    """Admin for the UTM medium lookup table."""

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
        """Add qr_preview as readonly, but only on the change view (obj != None)."""
        ro = list(super().get_readonly_fields(request, obj))
        if is_qr_enabled() and obj is not None:
            ro.append("qr_preview")
        return ro

    def get_fieldsets(self, request, obj=None):
        """Append QR Code fieldset on the change view when QR is configured."""
        fieldsets = list(super().get_fieldsets(request, obj))
        if is_qr_enabled() and obj is not None:
            fieldsets.append(("QR Code", {"fields": ("qr_preview",)}))
        return fieldsets

    @admin.display(description="QR Code")
    def qr_preview(self, obj):
        """Render an <img> tag using the configured QR Generation function."""
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
    list_filter = ("target", "country", "timestamp")
    readonly_fields = [field.name for field in ClickLog._meta.fields]

    actions = ["update_geolocation"]

    def has_add_permission(self, request):
        """Prevent adding new ClickLogs from the admin."""
        return False

    def update_geolocation(self, request, queryset):
        """Admin action to update geolocation (country, city) for selected ClickLogs."""
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


@admin.register(ClickReport)
class ClickReportAdmin(admin.ModelAdmin):
    """Admin dashboard showing aggregated click report data."""

    MAX_ROWS = 20

    def has_add_permission(self, request):
        """Reports are read-only — no adding."""
        return False

    def has_change_permission(self, request, obj=None):
        """Reports are read-only — no editing."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Reports are read-only — no deleting."""
        return False

    def changelist_view(self, request, extra_context=None):
        """Render the click report dashboard instead of the default changelist."""
        today = datetime.date.today()
        default_start = today - datetime.timedelta(days=30)

        start_str = request.GET.get("start", default_start.isoformat())
        end_str = request.GET.get("end", today.isoformat())

        try:
            start_date = datetime.date.fromisoformat(start_str)
        except ValueError:
            start_date = default_start

        try:
            end_date = datetime.date.fromisoformat(end_str)
        except ValueError:
            end_date = today

        qs = ClickLog.objects.filter(
            timestamp__date__gte=start_date,
            timestamp__date__lte=end_date,
        )
        total = qs.count()

        def _breakdown(qs, *fields):
            rows = list(
                qs.values(*fields)
                .annotate(count=Count("id"))
                .order_by("-count")
            )
            for row in rows:
                for f in fields:
                    if not row[f]:
                        row[f] = "(not set)"
                row["pct"] = round(row["count"] / total * 100, 1) if total else 0
            truncated = len(rows) - self.MAX_ROWS if len(rows) > self.MAX_ROWS else 0
            return rows[: self.MAX_ROWS], truncated

        by_source, source_extra = _breakdown(qs, "utm_source")
        by_medium, medium_extra = _breakdown(qs, "utm_medium")
        by_campaign, campaign_extra = _breakdown(qs, "utm_campaign")
        by_link, link_extra = _breakdown(qs, "target__name", "target__slug")
        by_country, country_extra = _breakdown(qs, "country")

        by_date = list(
            qs.values(date=TruncDate("timestamp"))
            .annotate(count=Count("id"))
            .order_by("date")
        )

        context = {
            **self.admin_site.each_context(request),
            "title": "Click Reports",
            "opts": self.model._meta,
            "start_date": start_str,
            "end_date": end_str,
            "total_clicks": total,
            "by_source": by_source,
            "source_extra": source_extra,
            "by_medium": by_medium,
            "medium_extra": medium_extra,
            "by_campaign": by_campaign,
            "campaign_extra": campaign_extra,
            "by_link": by_link,
            "link_extra": link_extra,
            "by_date": by_date,
            "by_country": by_country,
            "country_extra": country_extra,
        }
        return TemplateResponse(
            request,
            "admin/clickify/clickreport/change_list.html",
            context,
        )

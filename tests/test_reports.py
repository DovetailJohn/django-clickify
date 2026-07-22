import datetime

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from clickify.models import ClickLog, TrackedLink


class ClickReportAdminTestBase(TestCase):
    """Shared setup for report admin tests."""

    @classmethod
    def setUpTestData(cls):
        cls.staff_user = User.objects.create_user(
            username="staff", password="pass", is_staff=True
        )
        cls.link = TrackedLink.objects.create(
            name="Test Link",
            slug="test-link",
            target_url="https://example.com",
        )

    def setUp(self):
        self.client.login(username="staff", password="pass")
        self.url = reverse("admin:clickify_clickreport_changelist")


class TestReportPageLoads(ClickReportAdminTestBase):
    def test_report_page_returns_200(self):
        response = self.client.get(self.url)
        assert response.status_code == 200

    def test_report_page_contains_title(self):
        response = self.client.get(self.url)
        assert "Click Reports" in response.content.decode()


class TestPermissionCheck(TestCase):
    def test_anonymous_user_redirected_to_login(self):
        url = reverse("admin:clickify_clickreport_changelist")
        response = self.client.get(url)
        assert response.status_code == 302
        assert "/login/" in response.url


class TestDefaultDateRange(ClickReportAdminTestBase):
    def test_default_range_is_last_30_days(self):
        response = self.client.get(self.url)
        content = response.content.decode()
        today = datetime.date.today()
        default_start = today - datetime.timedelta(days=30)
        assert default_start.isoformat() in content
        assert today.isoformat() in content


class TestDateFiltering(ClickReportAdminTestBase):
    def test_date_range_filters_clicks(self):
        ClickLog.objects.create(
            target=self.link, ip_address="1.2.3.4", user_agent="bot",
            utm_source="email",
        )
        old_click = ClickLog.objects.create(
            target=self.link, ip_address="1.2.3.4", user_agent="bot",
            utm_source="google",
        )
        # Backdate one click to 90 days ago
        old_date = datetime.date.today() - datetime.timedelta(days=90)
        ClickLog.objects.filter(pk=old_click.pk).update(timestamp=old_date)

        # Default range (last 30 days) should show only 1 click
        response = self.client.get(self.url)
        content = response.content.decode()
        assert ">1<" in content.replace(" ", "")


class TestAllBreakdownsPresent(ClickReportAdminTestBase):
    def test_all_section_headings_present(self):
        ClickLog.objects.create(
            target=self.link, ip_address="1.2.3.4", user_agent="bot",
            utm_source="email", utm_medium="cpc", utm_campaign="spring",
            country="US",
        )
        response = self.client.get(self.url)
        content = response.content.decode()
        assert "By UTM Source" in content
        assert "By UTM Medium" in content
        assert "By Campaign" in content
        assert "By Tracked Link" in content
        assert "By Country" in content
        assert "Over Time (Daily)" in content


class TestEmptyState(ClickReportAdminTestBase):
    def test_no_clicks_shows_empty_message(self):
        response = self.client.get(self.url)
        assert "No clicks recorded in this date range." in response.content.decode()


class TestPercentages(ClickReportAdminTestBase):
    def test_percentage_calculation(self):
        for _ in range(3):
            ClickLog.objects.create(
                target=self.link, ip_address="1.2.3.4", user_agent="bot",
                utm_source="email",
            )
        for _ in range(7):
            ClickLog.objects.create(
                target=self.link, ip_address="1.2.3.4", user_agent="bot",
                utm_source="google",
            )
        response = self.client.get(self.url)
        content = response.content.decode()
        assert "30.0%" in content
        assert "70.0%" in content


class TestNullGrouping(ClickReportAdminTestBase):
    def test_null_utm_source_shows_not_set(self):
        ClickLog.objects.create(
            target=self.link, ip_address="1.2.3.4", user_agent="bot",
            utm_source=None,
        )
        response = self.client.get(self.url)
        assert "(not set)" in response.content.decode()


class TestTruncation(ClickReportAdminTestBase):
    def test_top_20_with_overflow_message(self):
        for i in range(25):
            ClickLog.objects.create(
                target=self.link, ip_address="1.2.3.4", user_agent="bot",
                utm_source=f"source-{i:02d}",
            )
        response = self.client.get(self.url)
        content = response.content.decode()
        assert "(and 5 more)" in content


class TestReadOnly(ClickReportAdminTestBase):
    def test_no_add_button(self):
        response = self.client.get(self.url)
        content = response.content.decode()
        assert "Add click report" not in content


class TestDrillDownFilter(ClickReportAdminTestBase):
    def test_single_filter_narrows_results(self):
        ClickLog.objects.create(
            target=self.link, ip_address="1.2.3.4", user_agent="bot",
            utm_source="email", utm_medium="cpc",
        )
        ClickLog.objects.create(
            target=self.link, ip_address="1.2.3.4", user_agent="bot",
            utm_source="google", utm_medium="organic",
        )
        response = self.client.get(self.url + "?utm_source=email")
        content = response.content.decode()
        assert "100.0%" in content
        assert "google" not in content

    def test_multi_filter_stacks(self):
        ClickLog.objects.create(
            target=self.link, ip_address="1.2.3.4", user_agent="bot",
            utm_source="email", utm_medium="cpc",
        )
        ClickLog.objects.create(
            target=self.link, ip_address="1.2.3.4", user_agent="bot",
            utm_source="email", utm_medium="organic",
        )
        ClickLog.objects.create(
            target=self.link, ip_address="1.2.3.4", user_agent="bot",
            utm_source="google", utm_medium="cpc",
        )
        response = self.client.get(
            self.url + "?utm_source=email&utm_medium=cpc"
        )
        content = response.content.decode()
        assert ">1<" in content.replace(" ", "")

    def test_filter_banner_shows_active_filters(self):
        ClickLog.objects.create(
            target=self.link, ip_address="1.2.3.4", user_agent="bot",
            utm_source="email",
        )
        response = self.client.get(self.url + "?utm_source=email")
        content = response.content.decode()
        assert "Filtered by:" in content
        assert "UTM Source" in content
        assert "email" in content

    def test_clear_all_link_present(self):
        ClickLog.objects.create(
            target=self.link, ip_address="1.2.3.4", user_agent="bot",
            utm_source="email",
        )
        response = self.client.get(self.url + "?utm_source=email")
        assert "Clear all" in response.content.decode()

    def test_not_set_filter_works(self):
        ClickLog.objects.create(
            target=self.link, ip_address="1.2.3.4", user_agent="bot",
            utm_source=None,
        )
        ClickLog.objects.create(
            target=self.link, ip_address="1.2.3.4", user_agent="bot",
            utm_source="email",
        )
        response = self.client.get(self.url + "?utm_source=(not+set)")
        content = response.content.decode()
        assert "100.0%" in content

    def test_invalid_filter_key_ignored(self):
        ClickLog.objects.create(
            target=self.link, ip_address="1.2.3.4", user_agent="bot",
            utm_source="email",
        )
        response = self.client.get(self.url + "?bogus_field=hack")
        assert response.status_code == 200
        assert "Filtered by:" not in response.content.decode()

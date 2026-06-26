from unittest.mock import patch, MagicMock

from django.core.exceptions import ValidationError
from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.core.cache import cache

from clickify.models import TrackedLink, UtmSource, UtmMedium, ClickLog, validate_forward_params
from clickify.utils import build_redirect_url


class BuildRedirectUrlTest(TestCase):
    """Unit tests for build_redirect_url — no DB hits needed for most cases."""

    def _make_link(self, target_url="https://dest.example.com/page", **kwargs):
        """Return an unsaved TrackedLink-like mock for pure logic tests."""
        link = MagicMock(spec=TrackedLink)
        link.target_url = target_url
        link.utm_source_id = None
        link.utm_medium_id = None
        link.utm_campaign = ""
        link.utm_content = ""
        link.utm_term = ""
        link.utm_override = False
        link.forward_params = ""
        for k, v in kwargs.items():
            setattr(link, k, v)
        return link

    def _req(self, params=None):
        """Return a GET request with the given query params."""
        rf = RequestFactory()
        return rf.get("/go/slug/", params or {})

    # --- no UTM anywhere ---

    def test_no_utm_returns_target_url_unchanged(self):
        link = self._make_link()
        result, _ = build_redirect_url(link, self._req())
        self.assertEqual(result, "https://dest.example.com/page")

    def test_no_target_url_returns_slash(self):
        link = self._make_link(target_url=None)
        result, _ = build_redirect_url(link, self._req())
        self.assertEqual(result, "/")

    def test_empty_target_url_returns_slash(self):
        link = self._make_link(target_url="")
        result, _ = build_redirect_url(link, self._req())
        self.assertEqual(result, "/")

    # --- pass-through (no stored UTM, visitor brings params) ---

    def test_incoming_utm_forwarded_when_no_stored_utm(self):
        link = self._make_link()
        result, _ = build_redirect_url(link, self._req({"utm_source": "social"}))
        self.assertIn("utm_source=social", result)

    def test_multiple_incoming_utm_all_forwarded(self):
        link = self._make_link()
        result, _ = build_redirect_url(
            link, self._req({"utm_source": "social", "utm_campaign": "winter"})
        )
        self.assertIn("utm_source=social", result)
        self.assertIn("utm_campaign=winter", result)

    # --- stored UTM only (no incoming) ---

    def test_stored_source_appended(self):
        source = MagicMock(spec=UtmSource, value="email")
        link = self._make_link(utm_source_id=1, utm_source=source)
        result, _ = build_redirect_url(link, self._req())
        self.assertIn("utm_source=email", result)

    def test_stored_source_medium_campaign_all_appended(self):
        source = MagicMock(spec=UtmSource, value="email")
        medium = MagicMock(spec=UtmMedium, value="email")
        link = self._make_link(
            utm_source_id=1, utm_source=source,
            utm_medium_id=1, utm_medium=medium,
            utm_campaign="q3-launch",
        )
        result, _ = build_redirect_url(link, self._req())
        self.assertIn("utm_source=email", result)
        self.assertIn("utm_medium=email", result)
        self.assertIn("utm_campaign=q3-launch", result)

    def test_utm_content_and_term_appended(self):
        source = MagicMock(spec=UtmSource, value="email")
        link = self._make_link(
            utm_source_id=1, utm_source=source,
            utm_content="header-cta",
            utm_term="running+shoes",
        )
        result, _ = build_redirect_url(link, self._req())
        self.assertIn("utm_content=header-cta", result)
        self.assertIn("utm_term=running%2Bshoes", result)

    # --- preserve mode (utm_override=False, the default) ---

    def test_preserve_mode_incoming_source_wins_over_stored(self):
        source = MagicMock(spec=UtmSource, value="email")
        link = self._make_link(utm_source_id=1, utm_source=source, utm_override=False)
        result, _ = build_redirect_url(link, self._req({"utm_source": "social"}))
        self.assertIn("utm_source=social", result)
        self.assertNotIn("utm_source=email", result)

    def test_preserve_mode_stored_fills_gap_when_not_in_incoming(self):
        source = MagicMock(spec=UtmSource, value="email")
        link = self._make_link(
            utm_source_id=1, utm_source=source,
            utm_campaign="q3",
            utm_override=False,
        )
        result, _ = build_redirect_url(
            link, self._req({"utm_source": "social"})
        )
        self.assertIn("utm_source=social", result)
        self.assertIn("utm_campaign=q3", result)

    # --- override mode (utm_override=True) ---

    def test_override_mode_stored_source_wins_over_incoming(self):
        source = MagicMock(spec=UtmSource, value="email")
        link = self._make_link(utm_source_id=1, utm_source=source, utm_override=True)
        result, _ = build_redirect_url(link, self._req({"utm_source": "social"}))
        self.assertIn("utm_source=email", result)
        self.assertNotIn("utm_source=social", result)

    def test_override_mode_stored_wins_over_all_incoming_utm(self):
        source = MagicMock(spec=UtmSource, value="email")
        link = self._make_link(
            utm_source_id=1, utm_source=source,
            utm_campaign="stored-campaign",
            utm_override=True,
        )
        result, _ = build_redirect_url(
            link, self._req({"utm_source": "social", "utm_campaign": "incoming-campaign"})
        )
        self.assertIn("utm_source=email", result)
        self.assertIn("utm_campaign=stored-campaign", result)
        self.assertNotIn("utm_source=social", result)
        self.assertNotIn("utm_campaign=incoming-campaign", result)

    # --- base URL params preservation ---

    def test_existing_base_url_params_preserved(self):
        source = MagicMock(spec=UtmSource, value="email")
        link = self._make_link(
            target_url="https://dest.example.com/page?foo=bar",
            utm_source_id=1, utm_source=source,
        )
        result, _ = build_redirect_url(link, self._req())
        self.assertIn("foo=bar", result)
        self.assertIn("utm_source=email", result)

    def test_base_url_params_preserved_with_no_utm(self):
        link = self._make_link(target_url="https://dest.example.com/page?foo=bar")
        result, _ = build_redirect_url(link, self._req())
        self.assertEqual(result, "https://dest.example.com/page?foo=bar")

    # --- forward_params allowlist ---

    def test_allowed_extra_param_forwarded(self):
        link = self._make_link(forward_params="name")
        result, _ = build_redirect_url(link, self._req({"name": "John"}))
        self.assertIn("name=John", result)

    def test_non_allowed_extra_param_dropped(self):
        link = self._make_link(forward_params="")
        result, _ = build_redirect_url(link, self._req({"name": "John"}))
        self.assertNotIn("name=John", result)

    def test_only_allowlisted_params_forwarded(self):
        link = self._make_link(forward_params="name")
        result, _ = build_redirect_url(
            link, self._req({"name": "John", "secret": "token"})
        )
        self.assertIn("name=John", result)
        self.assertNotIn("secret=token", result)

    def test_forward_params_with_spaces_and_empties_handled(self):
        link = self._make_link(forward_params=" name , , ref_id ")
        result, _ = build_redirect_url(
            link, self._req({"name": "John", "ref_id": "42"})
        )
        self.assertIn("name=John", result)
        self.assertIn("ref_id=42", result)

    def test_utm_param_in_forward_params_not_double_counted(self):
        # utm_* in the allowlist should not be forwarded via the extra path —
        # UTM handling is separate and the filter excludes utm_* keys.
        source = MagicMock(spec=UtmSource, value="email")
        link = self._make_link(
            utm_source_id=1, utm_source=source,
            forward_params="utm_source",  # should be ignored in extra path
            utm_override=True,
        )
        result, _ = build_redirect_url(link, self._req({"utm_source": "social"}))
        # stored wins in override mode; value is "email" not "social"
        self.assertIn("utm_source=email", result)
        self.assertNotIn("utm_source=social", result)


class UtmClickLogIntegrationTest(TestCase):
    """Integration tests: verify UTM params reach the ClickLog via the view."""

    def setUp(self):
        cache.clear()
        self.source = UtmSource.objects.create(value="email", label="Email Newsletter")
        self.medium = UtmMedium.objects.create(value="email", label="Email Campaign")
        self.link = TrackedLink.objects.create(
            name="UTM Test Link",
            slug="utm-test",
            target_url="https://dest.example.com/page",
            utm_source=self.source,
            utm_medium=self.medium,
            utm_campaign="q3-launch",
            utm_content="header-cta",
        )

    @patch("clickify.utils.get_client_ip", return_value=("1.2.3.4", True))
    @patch("clickify.utils.get_geolocation", return_value=("US", "New York"))
    def test_stored_utm_logged_on_click(self, mock_geo, mock_ip):
        url = reverse("clickify:track_click", kwargs={"slug": self.link.slug})
        self.client.get(url)
        log = ClickLog.objects.get(target=self.link)
        self.assertEqual(log.utm_source, "email")
        self.assertEqual(log.utm_medium, "email")
        self.assertEqual(log.utm_campaign, "q3-launch")
        self.assertEqual(log.utm_content, "header-cta")

    @patch("clickify.utils.get_client_ip", return_value=("1.2.3.4", True))
    @patch("clickify.utils.get_geolocation", return_value=("US", "New York"))
    def test_incoming_utm_logged_in_preserve_mode(self, mock_geo, mock_ip):
        url = reverse("clickify:track_click", kwargs={"slug": self.link.slug})
        self.client.get(url, {"utm_source": "social"})
        log = ClickLog.objects.get(target=self.link)
        # Preserve mode: incoming wins for source
        self.assertEqual(log.utm_source, "social")
        # Stored campaign still logged (visitor didn't bring it)
        self.assertEqual(log.utm_campaign, "q3-launch")

    @patch("clickify.utils.get_client_ip", return_value=("1.2.3.4", True))
    @patch("clickify.utils.get_geolocation", return_value=("US", "New York"))
    def test_stored_utm_wins_in_override_mode(self, mock_geo, mock_ip):
        self.link.utm_override = True
        self.link.save()
        url = reverse("clickify:track_click", kwargs={"slug": self.link.slug})
        self.client.get(url, {"utm_source": "social"})
        log = ClickLog.objects.get(target=self.link)
        self.assertEqual(log.utm_source, "email")

    @patch("clickify.utils.get_client_ip", return_value=("1.2.3.4", True))
    @patch("clickify.utils.get_geolocation", return_value=("US", "New York"))
    def test_no_utm_log_is_null_when_no_utm(self, mock_geo, mock_ip):
        bare_link = TrackedLink.objects.create(
            name="Bare Link", slug="bare", target_url="https://dest.example.com/"
        )
        url = reverse("clickify:track_click", kwargs={"slug": bare_link.slug})
        self.client.get(url)
        log = ClickLog.objects.get(target=bare_link)
        self.assertIsNone(log.utm_source)
        self.assertIsNone(log.utm_campaign)


class ValidateForwardParamsTest(TestCase):

    def _ok(self, value):
        """Assert value passes validation."""
        try:
            validate_forward_params(value)
        except ValidationError as e:
            self.fail(f"Unexpected ValidationError for {value!r}: {e}")

    def _bad(self, value):
        """Assert value raises ValidationError."""
        with self.assertRaises(ValidationError):
            validate_forward_params(value)

    # --- valid inputs ---

    def test_blank_is_valid(self):
        self._ok("")

    def test_single_name(self):
        self._ok("name")

    def test_multiple_names(self):
        self._ok("name, ref_id, campaign_token")

    def test_names_with_hyphens_underscores_dots(self):
        self._ok("ref-id, track.id, campaign_token")

    def test_trailing_comma_ignored(self):
        self._ok("name,")

    def test_extra_spaces_around_commas(self):
        self._ok("  name ,  ref_id  ")

    # --- invalid inputs ---

    def test_key_value_pair_rejected(self):
        self._bad("name=John")

    def test_utm_prefix_rejected(self):
        self._bad("utm_source")

    def test_utm_prefix_case_insensitive(self):
        self._bad("UTM_SOURCE")

    def test_spaces_within_token_rejected(self):
        self._bad("my param")

    def test_special_characters_rejected(self):
        self._bad("name[]")

    def test_mixed_valid_and_invalid_all_reported(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_forward_params("name, utm_source, ref_id=1")
        messages = " ".join(str(m) for m in ctx.exception.messages)
        self.assertIn("utm_source", messages)
        self.assertIn("ref_id=1", messages)

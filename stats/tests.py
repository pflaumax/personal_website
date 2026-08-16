from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from .middleware import PageViewMiddleware, _excluded_prefixes
from .models import PageView
from .purge import admin_path_prefix, purge_admin_pageviews


class StatsViewAccessTests(TestCase):
    """
    /api/stats/ is staff-only. It must never be reachable by non-staff, and
    must never redirect to the admin login page — that redirect would leak
    settings.ADMIN_URL via the Location header, as it used to.
    """

    def test_anonymous_gets_404_not_a_login_redirect(self):
        response = self.client.get(reverse("stats"))

        self.assertEqual(response.status_code, 404)
        self.assertNotIn("Location", response.headers)

    def test_non_staff_user_gets_404(self):
        User.objects.create_user("regular", password="pw")
        self.client.login(username="regular", password="pw")

        response = self.client.get(reverse("stats"))

        self.assertEqual(response.status_code, 404)

    def test_staff_user_gets_valid_json(self):
        User.objects.create_user("staffer", password="pw", is_staff=True)
        self.client.login(username="staffer", password="pw")

        response = self.client.get(reverse("stats"))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("summary", data)
        self.assertIn("pages", data)


class StatsViewLimitTests(TestCase):
    """
    ?limit= is user-controlled input. None of these values should ever
    reach a 500 (negative indexing / integer overflow into the DB layer).
    """

    def setUp(self):
        User.objects.create_user("staffer", password="pw", is_staff=True)
        self.client.login(username="staffer", password="pw")
        for i in range(5):
            PageView.objects.create(path=f"/page-{i}/", count=i + 1)

    def test_negative_limit_does_not_500(self):
        response = self.client.get(reverse("stats"), {"limit": "-1"})
        self.assertEqual(response.status_code, 200)

    def test_huge_limit_does_not_500(self):
        response = self.client.get(reverse("stats"), {"limit": "99999999999999999999"})

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(response.json()["pages"]), 100)

    def test_non_numeric_limit_falls_back_to_default(self):
        response = self.client.get(reverse("stats"), {"limit": "abc"})

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(response.json()["pages"]), 10)

    def test_zero_limit_returns_summary_without_pages(self):
        response = self.client.get(reverse("stats"), {"limit": "0"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["pages"], [])
        self.assertEqual(response.json()["summary"]["unique_pages"], 5)

    def test_limit_within_range_is_respected(self):
        response = self.client.get(reverse("stats"), {"limit": "2"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["pages"]), 2)


class StatsViewSummaryTests(TestCase):
    """Summary totals must cover every row, not just the limited slice."""

    def setUp(self):
        User.objects.create_user("staffer", password="pw", is_staff=True)
        self.client.login(username="staffer", password="pw")

    def test_summary_totals_are_not_limited(self):
        for i in range(15):
            PageView.objects.create(path=f"/page-{i}/", count=i + 1)

        response = self.client.get(reverse("stats"), {"limit": "5"})
        data = response.json()

        self.assertEqual(data["summary"]["unique_pages"], 15)
        self.assertEqual(data["summary"]["total_page_views"], sum(range(1, 16)))
        self.assertEqual(len(data["pages"]), 5)

    def test_summary_on_empty_table_is_zero_not_none(self):
        response = self.client.get(reverse("stats"))

        self.assertEqual(
            response.json()["summary"],
            {"total_page_views": 0, "unique_pages": 0},
        )
        self.assertEqual(response.json()["pages"], [])


class PageViewMiddlewareTests(TestCase):
    """
    Exercises the middleware directly instead of through the URL dispatcher,
    since a bare get_response stub is enough to control the response status
    the tracking decision depends on.
    """

    def setUp(self):
        self.factory = RequestFactory()
        _excluded_prefixes.cache_clear()
        self.addCleanup(_excluded_prefixes.cache_clear)

    @staticmethod
    def _middleware(status_code=200):
        return PageViewMiddleware(
            get_response=lambda request: HttpResponse(status=status_code)
        )

    @override_settings(ADMIN_URL="super-secret-panel")
    def test_admin_url_prefix_is_excluded(self):
        """
        Uses a value deliberately unlike "admin" so the exclusion can only be
        coming from the ADMIN_URL logic, not the hardcoded "/admin/" prefix.
        """
        middleware = self._middleware()
        for path in ("/super-secret-panel/", "/super-secret-panel/login/"):
            with self.subTest(path=path):
                middleware(self.factory.get(path))

        self.assertEqual(PageView.objects.count(), 0)

    @override_settings(ADMIN_URL="panel")
    def test_admin_prefix_does_not_swallow_similarly_named_pages(self):
        """A "/panel" prefix must not match the public page "/panel-talk/"."""
        self._middleware()(self.factory.get("/panel-talk/"))

        self.assertEqual(PageView.objects.get().path, "/panel-talk/")

    def test_tinymce_endpoints_are_not_tracked(self):
        middleware = self._middleware()
        for path in ("/tinymce/compressor/", "/tinymce/filebrowser/"):
            with self.subTest(path=path):
                middleware(self.factory.get(path))

        self.assertEqual(PageView.objects.count(), 0)

    def test_media_files_are_not_tracked(self):
        self._middleware()(self.factory.get("/media/media_files/clip.mp3"))

        self.assertEqual(PageView.objects.count(), 0)

    def test_over_length_path_is_not_tracked(self):
        """
        Truncating would collide distinct URLs into one unique row and
        misattribute their views, so an over-length path is skipped instead.
        """
        self._middleware()(self.factory.get("/" + "a" * 1000))

        self.assertEqual(PageView.objects.count(), 0)

    def test_path_at_the_length_limit_is_tracked(self):
        path = "/" + "a" * 511  # exactly MAX_TRACKED_PATH_LENGTH

        self._middleware()(self.factory.get(path))

        self.assertEqual(PageView.objects.get().path, path)

    def test_ordinary_path_is_tracked(self):
        self._middleware()(self.factory.get("/blog/"))

        self.assertEqual(PageView.objects.get().path, "/blog/")
        self.assertEqual(PageView.objects.get().count, 1)

    def test_404_response_is_not_tracked(self):
        self._middleware(status_code=404)(self.factory.get("/does-not-exist/"))

        self.assertEqual(PageView.objects.count(), 0)

    def test_500_response_is_not_tracked(self):
        self._middleware(status_code=500)(self.factory.get("/blog/"))

        self.assertEqual(PageView.objects.count(), 0)

    def test_redirects_are_not_tracked(self):
        """
        A redirect never rendered the page. Counting it would double-count
        every visit to a retired URL (once here, once at the target).
        """
        for status_code in (301, 302):
            with self.subTest(status_code=status_code):
                PageView.objects.all().delete()

                self._middleware(status_code=status_code)(self.factory.get("/home/"))

                self.assertEqual(PageView.objects.count(), 0)

    def test_media_list_endpoint_is_not_tracked(self):
        """/media-list/ is a JSON API for the admin's TinyMCE picker."""
        self._middleware()(self.factory.get("/media-list/"))

        self.assertEqual(PageView.objects.count(), 0)

    @override_settings(ADMIN_URL="/")
    def test_degenerate_admin_url_does_not_disable_all_tracking(self):
        """A "/" ADMIN_URL must not turn into a prefix matching every path."""
        self._middleware()(self.factory.get("/blog/"))

        self.assertEqual(PageView.objects.get().path, "/blog/")

    def test_repeated_requests_increment_exactly_once_each(self):
        middleware = self._middleware()

        for _ in range(5):
            middleware(self.factory.get("/blog/"))

        self.assertEqual(PageView.objects.get(path="/blog/").count, 5)

    def test_existing_path_increments_with_a_single_query(self):
        """
        Scoped to the middleware rather than a full page render, so unrelated
        queries added elsewhere in the request path can't break this.
        """
        PageView.objects.create(path="/blog/", count=1)

        with self.assertNumQueries(1):
            self._middleware()(self.factory.get("/blog/"))

        self.assertEqual(PageView.objects.get(path="/blog/").count, 2)


class PageViewMiddlewareIntegrationTests(TestCase):
    """Runs through the real URL dispatcher to confirm end-to-end wiring."""

    def test_page_visit_is_tracked_through_the_real_stack(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(PageView.objects.get(path="/").count, 1)


class AdminPathPrefixTests(TestCase):
    """
    admin_path_prefix() guards a delete(). A degenerate admin URL must never
    resolve to "/", which would match every tracked path.
    """

    def test_degenerate_values_return_none(self):
        for admin_url in ("", "/", "///", None, "   "):
            with self.subTest(admin_url=admin_url):
                self.assertIsNone(admin_path_prefix(admin_url))

    def test_normal_values_get_wrapped_in_slashes(self):
        for admin_url, expected in (
            ("secret", "/secret/"),
            ("/secret", "/secret/"),
            ("/secret/", "/secret/"),
            ("deep/panel", "/deep/panel/"),
        ):
            with self.subTest(admin_url=admin_url):
                self.assertEqual(admin_path_prefix(admin_url), expected)


class PurgeAdminPageViewsTests(TestCase):
    def setUp(self):
        PageView.objects.create(path="/secret/", count=4)
        PageView.objects.create(path="/secret/login/", count=9)
        PageView.objects.create(path="/blog/", count=7)
        PageView.objects.create(path="/secret-diary/", count=3)

    def test_purges_only_paths_under_the_admin_prefix(self):
        deleted = purge_admin_pageviews(PageView, "secret")

        self.assertEqual(deleted, 2)
        self.assertCountEqual(
            PageView.objects.values_list("path", flat=True),
            ["/blog/", "/secret-diary/"],
        )

    def test_degenerate_admin_url_deletes_nothing(self):
        """The bug this guard exists for: "/" would have wiped the table."""
        for admin_url in ("/", "", "///"):
            with self.subTest(admin_url=admin_url):
                self.assertIsNone(purge_admin_pageviews(PageView, admin_url))

        self.assertEqual(PageView.objects.count(), 4)

    def test_is_idempotent(self):
        purge_admin_pageviews(PageView, "secret")
        second_run = purge_admin_pageviews(PageView, "secret")

        self.assertEqual(second_run, 0)
        self.assertEqual(PageView.objects.count(), 2)

    def test_command_refuses_degenerate_prefix(self):
        with self.assertRaises(CommandError):
            call_command("purge_admin_pageviews", "--prefix", "/")

        self.assertEqual(PageView.objects.count(), 4)

    def test_command_purges_rotated_prefix(self):
        call_command("purge_admin_pageviews", "--prefix", "secret", verbosity=0)

        self.assertEqual(PageView.objects.count(), 2)

    def test_command_dry_run_deletes_nothing(self):
        call_command(
            "purge_admin_pageviews", "--prefix", "secret", "--dry-run", verbosity=0
        )

        self.assertEqual(PageView.objects.count(), 4)

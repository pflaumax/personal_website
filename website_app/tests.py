from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.urls import reverse

from . import views
from .models import MediaFile, Post


class PublicPageSmokeTests(TestCase):
    """Baseline smoke tests for every publicly reachable website_app URL."""

    def test_index(self):
        response = self.client.get(reverse("website_app:index"))
        self.assertEqual(response.status_code, 200)

    def test_home_redirects_permanently_to_index(self):
        response = self.client.get(reverse("website_app:home"))
        self.assertRedirects(response, reverse("website_app:index"), status_code=301)

    def test_blog_empty(self):
        response = self.client.get(reverse("website_app:blog"))
        self.assertEqual(response.status_code, 200)

    def test_blog_lists_posts(self):
        owner = User.objects.create_user("author", password="pw")
        Post.objects.create(title="Hello World", content="<p>hi</p>", owner=owner)

        response = self.client.get(reverse("website_app:blog"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hello World")

    def test_post_detail(self):
        owner = User.objects.create_user("author", password="pw")
        post = Post.objects.create(
            title="Hello World", content="<p>hi</p>", owner=owner
        )

        response = self.client.get(reverse("website_app:post", args=[post.slug]))

        self.assertEqual(response.status_code, 200)

    def test_post_detail_missing_slug_404s(self):
        response = self.client.get(reverse("website_app:post", args=["does-not-exist"]))
        self.assertEqual(response.status_code, 404)

    def test_projects(self):
        response = self.client.get(reverse("website_app:projects"))
        self.assertEqual(response.status_code, 200)

    def test_contact(self):
        response = self.client.get(reverse("website_app:contact"))
        self.assertEqual(response.status_code, 200)

    def test_healthcheck(self):
        response = self.client.get(reverse("website_app:healthcheck"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "OK"})

    def test_media_list_requires_staff(self):
        """
        Anonymous requests get a plain 404, not a redirect to the admin
        login page — a redirect would leak settings.ADMIN_URL via Location.
        """
        response = self.client.get(reverse("website_app:media_list"))
        self.assertEqual(response.status_code, 404)
        self.assertNotIn("Location", response.headers)

    def test_media_list_accessible_to_staff(self):
        User.objects.create_user("staffer", password="pw", is_staff=True)
        self.client.login(username="staffer", password="pw")

        response = self.client.get(reverse("website_app:media_list"), {"type": "image"})

        self.assertEqual(response.status_code, 200)


class ErrorPageSmokeTests(TestCase):
    def test_404_page_renders(self):
        response = self.client.get("/this-page-does-not-exist/")
        self.assertEqual(response.status_code, 404)

    def test_admin_decoy_returns_404(self):
        """fadmin reuses error_404 verbatim — same template, same content."""
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "404", status_code=404)

    def test_error_views_render_with_matching_status_and_title(self):
        """
        Exercises the shared errors/_base.html factory directly, since
        error_500 only fires through handler500 on a real unhandled
        exception, which isn't practical to trigger through self.client.
        """
        request = RequestFactory().get("/whatever/")
        cases = [
            (views.error_400, 400),
            (views.error_403, 403),
            (views.error_404, 404),
            (views.error_500, 500),
        ]
        for view, status_code in cases:
            with self.subTest(status_code=status_code):
                response = view(request)
                self.assertEqual(response.status_code, status_code)
                self.assertContains(response, str(status_code), status_code=status_code)

    def test_contact_link_present_except_on_403(self):
        """
        403 (permission denied) has no contact link in the original copy;
        400/404/500 all point the visitor at the contact page. Checking for
        the "contact me" phrase rather than the bare /contact/ URL, since
        base.html's nav links to /contact/ on every page regardless.
        """
        request = RequestFactory().get("/whatever/")

        self.assertContains(views.error_400(request), "contact me", status_code=400)
        self.assertNotContains(views.error_403(request), "contact me", status_code=403)
        self.assertContains(views.error_404(request), "contact me", status_code=404)
        self.assertContains(views.error_500(request), "contact me", status_code=500)


class PostSlugTests(TestCase):
    """
    Covers Post.save()'s slug generation (website_app/models.py), which is
    load-bearing for permalinks and risky to touch without coverage.
    """

    def setUp(self):
        self.owner = User.objects.create_user("author", password="pw")

    def test_new_post_gets_slug_from_title(self):
        post = Post.objects.create(title="My First Post", content="x", owner=self.owner)
        self.assertEqual(post.slug, "my-first-post")

    def test_duplicate_title_gets_numeric_suffix(self):
        Post.objects.create(title="Same Title", content="x", owner=self.owner)
        second = Post.objects.create(title="Same Title", content="x", owner=self.owner)
        third = Post.objects.create(title="Same Title", content="x", owner=self.owner)

        self.assertEqual(second.slug, "same-title-1")
        self.assertEqual(third.slug, "same-title-2")

    def test_changing_title_regenerates_slug(self):
        post = Post.objects.create(
            title="Original Title", content="x", owner=self.owner
        )
        original_slug = post.slug

        post.title = "Updated Title"
        post.save()

        self.assertNotEqual(post.slug, original_slug)
        self.assertEqual(post.slug, "updated-title")

    def test_saving_without_title_change_keeps_slug(self):
        post = Post.objects.create(title="Stable Title", content="x", owner=self.owner)
        original_slug = post.slug

        post.content = "updated body"
        post.save()

        self.assertEqual(post.slug, original_slug)


class MediaFileSaveLoggingTests(TestCase):
    """
    MediaFile.save() used to print diagnostics to stdout; it now logs them.
    Deliberately never assigns a `file` here — this environment's S3Boto3Storage
    points at a real bucket (see S3FileField), and assigning file content would
    write to it. See website_app/models.py for the S3-at-import-time issue that
    makes storage untestable without hitting the real backend.
    """

    def test_save_without_a_file_logs_instead_of_printing(self):
        with self.assertLogs("website_app.models", level="DEBUG") as captured:
            media = MediaFile.objects.create(title="No File Yet", file_type="audio")

        self.assertTrue(media.pk)
        self.assertTrue(any("No File Yet" in line for line in captured.output))

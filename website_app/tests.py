from urllib.parse import quote

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import RequestFactory, TestCase
from django.urls import reverse

from . import views
from .media_urls import LEGACY_S3_MEDIA_PREFIX, rewrite_content, rewrite_posts
from .models import MediaFile, Post
from .projects_data import PROJECTS


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


class PageMetadataTests(TestCase):
    """
    Every page used to ship the same hardcoded <title> and description, which
    made every shared link preview identical.
    """

    def setUp(self):
        self.owner = User.objects.create_user("metaauthor", password="pw")
        self.post = Post.objects.create(
            title="A Metadata Post",
            content="<p>The opening sentence of the body.</p>",
            owner=self.owner,
        )

    def test_home_uses_the_bare_site_name(self):
        body = self.client.get(reverse("website_app:index")).content.decode()

        self.assertIn("<title>Max Pflaum</title>", body)

    def test_inner_page_title_is_prefixed(self):
        body = self.client.get(reverse("website_app:projects")).content.decode()

        self.assertIn("<title>Projects — Max Pflaum</title>", body)

    def test_post_title_and_description_come_from_the_post(self):
        body = self.client.get(self.post.get_absolute_url()).content.decode()

        self.assertIn("<title>A Metadata Post — Max Pflaum</title>", body)
        self.assertIn("The opening sentence of the body.", body)
        self.assertIn('property="og:type" content="article"', body)

    def test_canonical_url_has_no_query_string(self):
        body = self.client.get(
            self.post.get_absolute_url(), {"utm_source": "somewhere"}
        ).content.decode()

        self.assertIn(
            f'<link rel="canonical" href="http://testserver{self.post.get_absolute_url()}">',
            body,
        )
        self.assertNotIn("utm_source", body)

    def test_error_pages_are_noindex_but_real_pages_are_not(self):
        missing = self.client.get("/definitely-not-a-page/").content.decode()
        home = self.client.get(reverse("website_app:index")).content.decode()

        self.assertIn('name="robots" content="noindex"', missing)
        self.assertNotIn("noindex", home)


class HomeLatestProjectsTests(TestCase):
    """
    Home's "Latest projects" is a slice of the same tuple /projects/ renders,
    not a second copy of the markup. These lock that: adding or reordering an
    entry in projects_data.py has to move both pages together.
    """

    def test_home_shows_the_first_three_entries_of_the_tuple(self):
        response = self.client.get(reverse("website_app:index"))

        for project in PROJECTS[:3]:
            self.assertContains(response, project["title"])

    def test_home_shows_only_three(self):
        response = self.client.get(reverse("website_app:index"))

        for project in PROJECTS[3:]:
            self.assertNotContains(response, project["title"])

    def test_projects_page_shows_every_entry(self):
        response = self.client.get(reverse("website_app:projects"))

        for project in PROJECTS:
            self.assertContains(response, project["title"])

    def test_the_latest_list_draws_one_rule_above_it_not_two(self):
        """
        .latest-row:first-child already carries a border-top; a section-rule
        <hr> above it landed 22px away and read as a doubled line.
        """
        response = self.client.get(reverse("website_app:index"))

        self.assertNotContains(response, "section-rule")


class MeltEasterEggTests(TestCase):
    """
    The glitch filter: home page only, triggered by the wordmark. Scope is the
    thing to protect — a filtered ancestor turns position: fixed into absolute,
    and post pages carry a fixed back-to-top inside <main>.
    """

    def test_home_carries_the_filter_the_trigger_and_the_script(self):
        response = self.client.get(reverse("website_app:index"))

        self.assertContains(response, 'id="melt"')
        self.assertContains(response, "data-melt-trigger")
        self.assertContains(response, "data-melt-target")
        self.assertContains(response, "js/melt.")

    def test_the_wordmark_is_a_button_on_home_and_a_link_everywhere_else(self):
        """
        On home the wordmark linked to the page you were already on, so the
        easter egg takes that slot. A real button, not a link that refuses to
        navigate.
        """
        home = self.client.get(reverse("website_app:index"))
        self.assertContains(home, "logotype-mark")

        for name in "blog", "projects", "contact":
            other = self.client.get(reverse(f"website_app:{name}"))
            self.assertNotContains(other, "logotype-mark")

    def test_no_other_page_can_be_melted(self):
        owner = User.objects.create_user("meltauthor", password="pw")
        post = Post.objects.create(title="A Post", content="<p>x</p>", owner=owner)

        for url in (
            reverse("website_app:blog"),
            reverse("website_app:projects"),
            reverse("website_app:contact"),
            reverse("website_app:post", args=[post.slug]),
        ):
            response = self.client.get(url)
            self.assertNotContains(response, 'id="melt"')
            self.assertNotContains(response, "data-melt-trigger")


class PostPageFurnitureTests(TestCase):
    """
    The way out of a post and the ways to pass it on: the back link, the two
    share targets and the pair of back-to-top controls.
    """

    def setUp(self):
        self.owner = User.objects.create_user("shareauthor", password="pw")
        self.post = Post.objects.create(
            title="A Post To Share", content="<p>body</p>", owner=self.owner
        )
        self.url = reverse("website_app:post", args=[self.post.slug])

    def test_post_links_back_to_the_list(self):
        response = self.client.get(self.url)

        self.assertContains(response, 'class="post-back"')
        self.assertContains(response, f'href="{reverse("website_app:blog")}"')

    def test_share_targets_carry_the_absolute_post_url(self):
        response = self.client.get(self.url)
        absolute = f"http://testserver{self.post.get_absolute_url()}"

        self.assertContains(response, "bsky.app/intent/compose")
        self.assertContains(response, "mailto:?")
        self.assertEqual(response.context["share_url"], absolute)
        for value in (
            response.context["share_bluesky_url"],
            response.context["share_email_url"],
        ):
            self.assertIn(quote(absolute, safe=""), value)
            self.assertIn(quote(self.post.title, safe=""), value)

    def test_share_icons_carry_accessible_names(self):
        """
        Three glyphs and no visible words: with the label gone, these names are
        the only thing standing between a screen reader and three empty links.
        """
        response = self.client.get(self.url)

        self.assertContains(response, 'aria-label="Share this post"')
        self.assertContains(response, 'aria-label="Share on Bluesky"')
        self.assertContains(response, 'aria-label="Share by email"')
        self.assertContains(response, 'aria-label="Copy link to this post"')
        self.assertNotContains(response, "post-share-label")

    def test_copy_link_button_ships_hidden_and_knows_the_url(self):
        """
        share.js reveals it only where the clipboard API exists. A control that
        silently does nothing is worse than one that is not there.
        """
        response = self.client.get(self.url)
        absolute = f"http://testserver{self.post.get_absolute_url()}"

        self.assertContains(response, "data-copy-link")
        self.assertContains(response, f'data-url="{absolute}"')
        self.assertContains(response, "hidden data-copy-link")
        self.assertContains(response, 'role="status" data-copy-status')

    def test_no_advertising_funded_share_targets(self):
        """The whole point of the list: X, Telegram, Reddit and Facebook are out."""
        body = self.client.get(self.url).content.decode()

        for host in "twitter.com", "x.com", "t.me", "telegram", "reddit", "facebook":
            self.assertNotIn(host, body.lower())

    def test_share_urls_encode_spaces_as_percent_twenty(self):
        """
        urlencode defaults to quote_plus, and a mail client pastes the body
        verbatim — `+` for a space would reach the reader as a literal plus.
        """
        response = self.client.get(self.url)

        for key in "share_bluesky_url", "share_email_url":
            value = response.context[key]
            self.assertIn("%20", value)
            self.assertNotIn("+", value)

    def test_back_to_top_is_docked_and_floating(self):
        """
        Two controls, one accessible name: the floating twin is a mouse
        convenience, so it stays out of the tab order and out of the tree.
        """
        response = self.client.get(self.url)
        body = response.content.decode()

        self.assertEqual(body.count('href="#top"'), 2)
        self.assertIn("data-back-to-top-float", body)
        self.assertIn('aria-hidden="true" tabindex="-1"', body)
        # Manifest storage hashes the filename, so match the stem only.
        self.assertIn("js/back-to-top.", body)
        self.assertIn("js/share.", body)

    def test_the_list_page_has_no_share_or_back_furniture(self):
        response = self.client.get(reverse("website_app:blog"))

        self.assertNotContains(response, "post-share")
        self.assertNotContains(response, "back-to-top")


class BlogIndexFeedLinkTests(TestCase):
    """The feed rides the "Posts" heading as a glyph, not as a word in a row."""

    def test_feed_link_is_an_icon_with_an_accessible_name(self):
        response = self.client.get(reverse("website_app:blog"))

        self.assertContains(response, 'class="rss-link"')
        self.assertContains(response, 'aria-label="RSS feed"')
        self.assertContains(response, f'href="{reverse("website_app:feed")}"')
        # The old text link lived in a head-aside at the far end of the row.
        self.assertNotContains(response, "head-aside")


class FeedTests(TestCase):
    """
    Covers the RSS feed. The interesting part is item_pubdate: Post.date_added
    is a DateField, but pubDate needs an aware datetime, so a bare date here
    either warns or serialises wrong.
    """

    def setUp(self):
        self.owner = User.objects.create_user("feedauthor", password="pw")
        self.post = Post.objects.create(
            title="A Feed Post",
            # A single-escaped entity, which is what TinyMCE actually stores.
            content=(
                "<p>Body with a&nbsp;non-breaking space and "
                "<strong>markup</strong>.</p>"
            ),
            owner=self.owner,
        )

    def test_feed_is_served_as_browsable_xml(self):
        """
        Not application/rss+xml: browsers have no renderer for it and download
        the file instead of showing the feed.
        """
        response = self.client.get(reverse("website_app:feed"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("application/xml", response["Content-Type"])
        self.assertNotIn("rss+xml", response["Content-Type"])

    def test_feed_contains_post_with_absolute_link_and_pubdate(self):
        body = self.client.get(reverse("website_app:feed")).content.decode()

        self.assertIn("<title>A Feed Post</title>", body)
        self.assertIn(f"http://testserver{self.post.get_absolute_url()}", body)
        self.assertIn("<pubDate>", body)

    def test_summary_is_plain_text_without_tags_or_entities(self):
        body = self.client.get(reverse("website_app:feed")).content.decode()

        self.assertNotIn("&lt;strong&gt;", body)
        self.assertNotIn("&amp;nbsp;", body)
        self.assertIn("Body with a non-breaking space and markup.", body)

    def test_get_absolute_url_points_at_the_post(self):
        self.assertEqual(
            self.post.get_absolute_url(),
            reverse("website_app:post", kwargs={"slug": self.post.slug}),
        )


class MediaFileSaveLoggingTests(TestCase):
    """
    MediaFile.save() used to print diagnostics to stdout; it now logs them.
    Deliberately never assigns a `file` here, so the test never writes through
    whichever backend STORAGES["default"] resolves to in this environment.
    """

    def test_save_without_a_file_logs_instead_of_printing(self):
        with self.assertLogs("website_app.models", level="DEBUG") as captured:
            media = MediaFile.objects.create(title="No File Yet", file_type="audio")

        self.assertTrue(media.pk)
        self.assertTrue(any("No File Yet" in line for line in captured.output))


class RewriteContentTests(TestCase):
    """
    The S3 bucket these URLs pointed at is gone, so every absolute reference is
    a broken image. rewrite_content() is the pure half of the fix.
    """

    def test_absolute_s3_url_becomes_site_relative(self):
        body = f'<img src="{LEGACY_S3_MEDIA_PREFIX}media_files/nvim.webp">'

        new_body, replacements = rewrite_content(body)

        self.assertEqual(replacements, 1)
        self.assertEqual(new_body, '<img src="/media/media_files/nvim.webp">')

    def test_audio_and_image_in_one_body_are_both_rewritten(self):
        body = (
            f'<img src="{LEGACY_S3_MEDIA_PREFIX}media_files/f75.webp">'
            f'<audio src="{LEGACY_S3_MEDIA_PREFIX}media_files/asmr_75.mp3"></audio>'
        )

        new_body, replacements = rewrite_content(body)

        self.assertEqual(replacements, 2)
        self.assertNotIn("amazonaws.com", new_body)

    def test_is_idempotent(self):
        body = f'<img src="{LEGACY_S3_MEDIA_PREFIX}media_files/nvim.webp">'

        once, _ = rewrite_content(body)
        twice, replacements = rewrite_content(once)

        self.assertEqual(replacements, 0)
        self.assertEqual(once, twice)

    def test_unrelated_urls_are_left_alone(self):
        body = '<a href="https://example.com/media/thing.png">link</a>'

        new_body, replacements = rewrite_content(body)

        self.assertEqual(replacements, 0)
        self.assertEqual(new_body, body)

    def test_empty_content_does_not_crash(self):
        for value in ("", None):
            with self.subTest(value=value):
                self.assertEqual(rewrite_content(value), (value, 0))


class RewriteMediaUrlsCommandTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("author", password="pw")
        self.post = Post.objects.create(
            title="Uses The Tools I Use",
            content=f'<img src="{LEGACY_S3_MEDIA_PREFIX}media_files/nvim.webp">',
            owner=self.owner,
        )
        self.untouched = Post.objects.create(
            title="Plain Post", content="<p>no media here</p>", owner=self.owner
        )

    def test_dry_run_writes_nothing(self):
        call_command("rewrite_media_urls", "--dry-run", verbosity=0)

        self.post.refresh_from_db()
        self.assertIn("amazonaws.com", self.post.content)

    def test_command_rewrites_only_affected_posts(self):
        call_command("rewrite_media_urls", verbosity=0)

        self.post.refresh_from_db()
        self.untouched.refresh_from_db()

        self.assertNotIn("amazonaws.com", self.post.content)
        self.assertIn("/media/media_files/nvim.webp", self.post.content)
        self.assertEqual(self.untouched.content, "<p>no media here</p>")

    def test_rewriting_does_not_disturb_the_slug(self):
        """
        rewrite_posts() writes via queryset.update() precisely so Post.save()'s
        slug regeneration never runs. A changed permalink would break links.
        """
        original_slug = self.post.slug

        call_command("rewrite_media_urls", verbosity=0)

        self.post.refresh_from_db()
        self.assertEqual(self.post.slug, original_slug)

    def test_running_twice_is_a_no_op(self):
        call_command("rewrite_media_urls", verbosity=0)
        second_run = rewrite_posts(Post)

        self.assertEqual(second_run, [])

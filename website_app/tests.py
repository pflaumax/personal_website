from importlib import import_module
from pathlib import Path
from unittest import mock
from urllib.parse import quote

from django import forms
from django.contrib.admin.sites import site
from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import OperationalError
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import SafeString
from tinymce.widgets import TinyMCE

from . import views
from .admin import PostAdmin
from .figures import fingerprint, strip_figures
from .media_urls import LEGACY_S3_MEDIA_PREFIX, rewrite_content, rewrite_posts
from .models import MediaFile, Post
from .post_text import plain_text
from .projects_data import PROJECTS
from .templatetags.figures import figures

# The predicate stays inside the migration deliberately — a backfill rule that
# lived in app code could be edited later and retroactively change what an
# already-applied migration meant. import_module is the way in, since the
# module name is not a valid identifier.
needs_raw_html = import_module(
    "website_app.migrations.0011_post_raw_html"
).needs_raw_html


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

    def test_healthcheck_reports_database_down(self):
        """A dead database must turn the probe red, not leave it at 200."""
        with mock.patch.object(
            views.connection, "cursor", side_effect=OperationalError("down")
        ):
            response = self.client.get(reverse("website_app:healthcheck"))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(), {"status": "error", "database": "unavailable"}
        )
        self.assertNotIn("down", response.content.decode())

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

    The rule is: derive once, on the first save, then leave it alone. A slug is
    a published URL, and re-deriving it from an edited title moves that URL
    without anyone asking.
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

    def test_changing_the_title_leaves_the_permalink_alone(self):
        """
        The regression this guards: a post published at /blog/arpa-domain/ under
        the title "The domain took twenty minutes…" would have had its URL
        rewritten into the whole slugified sentence by the first typo fix.
        """
        post = Post.objects.create(
            title="The domain took twenty minutes.",
            content="x",
            owner=self.owner,
            slug="arpa-domain",
        )

        post.title = "The domain took twenty minutes. The backslash took three."
        post.save()

        post.refresh_from_db()
        self.assertEqual(post.slug, "arpa-domain")

    def test_a_hand_picked_slug_is_not_overwritten_on_creation(self):
        """What scripts/publish_post.py relies on to place a post at a URL."""
        post = Post.objects.create(
            title="A Very Long Title Nobody Wants In A URL",
            content="x",
            owner=self.owner,
            slug="short-one",
        )

        self.assertEqual(post.slug, "short-one")

    def test_clearing_the_slug_asks_for_a_new_one(self):
        """The deliberate way to rename: SlugField is blank=True and editable."""
        post = Post.objects.create(title="First Title", content="x", owner=self.owner)

        post.title = "Second Title"
        post.slug = ""
        post.save()

        self.assertEqual(post.slug, "second-title")

    def test_a_title_with_no_ascii_letters_still_gets_a_usable_slug(self):
        """
        slugify() drops what it cannot transliterate and returns "" for a title
        like this. An empty slug is not a cosmetic problem: get_absolute_url
        raises NoReverseMatch, so the post exists and nothing can link to it.
        """
        post = Post.objects.create(title="Привіт, світе", content="x", owner=self.owner)

        self.assertTrue(post.slug)
        self.assertEqual(post.slug, f"post-{timezone.localdate():%Y-%m-%d}")
        self.assertEqual(post.get_absolute_url(), f"/blog/{post.slug}/")

    def test_two_such_titles_do_not_collide(self):
        first = Post.objects.create(title="Привіт", content="x", owner=self.owner)
        second = Post.objects.create(title="Дякую", content="x", owner=self.owner)

        self.assertNotEqual(first.slug, second.slug)
        self.assertEqual(second.slug, f"{first.slug}-1")

    def test_the_derived_slug_passes_the_fields_own_validation(self):
        """
        SlugField here is declared without allow_unicode, so a slugify(…,
        allow_unicode=True) fallback would have produced values the admin form
        rejects. Whatever save() derives has to survive full_clean().
        """
        post = Post.objects.create(title="Привіт, світе", content="x", owner=self.owner)

        post.full_clean()

    def test_saving_without_title_change_keeps_slug(self):
        post = Post.objects.create(title="Stable Title", content="x", owner=self.owner)
        original_slug = post.slug

        post.content = "updated body"
        post.save()

        self.assertEqual(post.slug, original_slug)


class PostExcerptTests(TestCase):
    """
    Covers Post.excerpt() (website_app/models.py). strip_tags keeps the text
    between the tags it removes, so a post carrying an inline <style> or
    <script> block leaks raw CSS into the blog card, the RSS summary and the
    meta description — none of which are visible while writing the post.
    """

    def setUp(self):
        self.owner = User.objects.create_user("excerpt-author", password="pw")

    def _post(self, content):
        return Post.objects.create(title="Filters", content=content, owner=self.owner)

    def test_style_block_is_not_part_of_the_excerpt(self):
        post = self._post(
            "<style>.fx { margin: 2rem; color: red; }</style>"
            "<p>Real prose starts here.</p>"
        )
        self.assertEqual(post.excerpt(), "Real prose starts here.")

    def test_script_block_is_not_part_of_the_excerpt(self):
        post = self._post("<script>var x = 1;</script><p>Real prose starts here.</p>")
        self.assertEqual(post.excerpt(), "Real prose starts here.")

    def test_stripped_block_still_separates_surrounding_words(self):
        # Substituting a space, not "", keeps two words from being glued
        # together when a block sits between them.
        post = self._post("<p>before</p><style>.a{}</style><p>after</p>")
        self.assertEqual(post.excerpt(), "before after")

    def test_ordinary_markup_is_unaffected(self):
        post = self._post("<p>Plain <strong>post</strong> body.</p>")
        self.assertEqual(post.excerpt(), "Plain post body.")


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

    def test_link_previews_get_an_absolute_image_and_a_large_card(self):
        """
        Scrapers fetch og:image out of band, with no page to resolve a relative
        path against — a relative URL here silently yields no preview at all.
        """
        body = self.client.get(reverse("website_app:index")).content.decode()

        self.assertIn('property="og:image" content="http://testserver/static/', body)
        self.assertIn('name="twitter:image" content="http://testserver/static/', body)
        self.assertIn('content="summary_large_image"', body)
        self.assertIn('property="og:image:width" content="1200"', body)
        self.assertNotIn('name="twitter:card" content="summary"', body)

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

    def test_press_links_sit_on_the_project_they_are_about(self):
        """
        Both write-ups cover the ESP32 dashboard, so they belong on that entry
        rather than in the home page bio — and they must not leak onto home,
        which shows the first three projects.
        """
        projects = self.client.get(reverse("website_app:projects"))

        self.assertContains(projects, "Written up in")
        self.assertContains(projects, "xda-developers.com")
        self.assertContains(projects, "hackaday.com")

    def test_projects_page_says_where_the_titles_go(self):
        """
        The titles are external links to GitHub and look like plain headings
        until hovered, so the list says so once at the top.
        """
        response = self.client.get(reverse("website_app:projects"))

        self.assertContains(response, "Titles link straight to GitHub")

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
        self.assertContains(response, "js/melt.")

    def test_the_target_is_the_whole_container_not_just_main(self):
        """
        Header, main and footer melt together — half a melted page reads as a
        rendering bug rather than a joke.
        """
        body = self.client.get(reverse("website_app:index")).content.decode()

        self.assertIn('class="container" data-melt-target', body)

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
            self.assertNotContains(response, "data-melt-target")


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


class FigureTokenTests(TestCase):
    """
    Covers website_app/templatetags/figures.py — the mechanism that lets a post
    body stay editable in TinyMCE while its diagrams stay in git.

    The contract is narrow on purpose: a token is plain text the editor cannot
    break, an unknown name degrades to visible text rather than an exception,
    and the name pattern is also the path guard.
    """

    FIGURE = "ms-ui-gothic-widths"

    def test_a_known_token_is_replaced_by_its_partial(self):
        rendered = figures(f"<p>before</p>[[figure:{self.FIGURE}]]<p>after</p>")

        self.assertNotIn("[[figure:", rendered)
        self.assertIn('<figure class="fig">', rendered)
        self.assertIn("<p>before</p>", rendered)
        self.assertIn("<p>after</p>", rendered)

    def test_the_result_is_marked_safe_so_the_body_is_not_escaped(self):
        rendered = figures("<p>prose &amp; markup</p>")

        self.assertIsInstance(rendered, SafeString)
        self.assertEqual(rendered, "<p>prose &amp; markup</p>")

    def test_an_unknown_figure_is_left_on_the_page_and_logged(self):
        """
        Visible failure, not a 500: one wrong paragraph beats losing the post,
        and an unexpanded token is impossible to miss while proofreading.
        """
        with self.assertLogs("website_app.figures", "WARNING") as logs:
            rendered = figures("<p>x</p>[[figure:no-such-figure]]")

        self.assertIn("[[figure:no-such-figure]]", rendered)
        self.assertIn("no-such-figure", logs.output[0])

    def test_names_outside_the_pattern_are_not_tokens(self):
        """
        The pattern allows lowercase, digits and hyphens, which is what keeps a
        body from addressing anything outside the figures directory — no dot and
        no slash can reach the template loader.
        """
        for body in (
            "[[figure:../../base]]",
            "[[figure:Foo]]",
            "[[figure:foo bar]]",
            "[[figure:foo.html]]",
            "[[figure:]]",
        ):
            with self.subTest(body=body):
                self.assertEqual(figures(body), body)

    def test_repeated_tokens_all_expand(self):
        rendered = figures(f"[[figure:{self.FIGURE}]][[figure:{self.FIGURE}]]")

        self.assertEqual(rendered.count('<figure class="fig">'), 2)

    def test_empty_content_does_not_crash(self):
        self.assertEqual(figures(""), "")
        self.assertEqual(figures(None), "")

    def test_the_figure_needs_no_javascript(self):
        """
        The bar widths are written inline. They used to be applied by an
        IntersectionObserver, which was the only reason this figure needed a
        script — and meant the chart read as all-zero until scrolled into view.
        """
        rendered = figures(f"[[figure:{self.FIGURE}]]")

        self.assertNotIn("<script", rendered)
        self.assertNotIn("data-target", rendered)
        self.assertIn("width: 100%", rendered)
        self.assertIn("width: 67%", rendered)

    def test_the_figure_carries_no_palette_of_its_own(self):
        """Figures consume the site's tokens so both themes follow the page."""
        rendered = figures(f"[[figure:{self.FIGURE}]]")

        self.assertNotIn("#", rendered)

    def test_every_figure_on_disk_renders(self):
        """
        A figure is only reachable by name, so a broken one fails at read time
        for a reader rather than at deploy time for me. Render them all.
        """
        names = sorted(
            path.stem
            for path in (
                Path(__file__).parent / "templates" / "website_app" / "figures"
            ).glob("*.html")
        )

        self.assertTrue(names, "no figure partials found")
        for name in names:
            with self.subTest(figure=name):
                rendered = figures(f"[[figure:{name}]]")
                self.assertNotIn("[[figure:", rendered)
                self.assertIn("<figure", rendered)
                self.assertIn("<figcaption", rendered)

    def test_no_figure_needs_javascript(self):
        """
        The point of extracting these was that every demo in the post turned out
        to be decoration: an animation, a toggle that hid half of a comparison,
        a clock. If a figure grows a script it belongs in a static JS file, not
        inline in a partial.
        """
        names = sorted(
            path.stem
            for path in (
                Path(__file__).parent / "templates" / "website_app" / "figures"
            ).glob("*.html")
        )

        for name in names:
            with self.subTest(figure=name):
                self.assertNotIn("<script", figures(f"[[figure:{name}]]"))

    def test_the_glyph_figure_shows_both_outlines_at_once(self):
        """
        It replaced a button that swapped one polygon for another, which hid
        half of the comparison the figure exists to make.
        """
        rendered = figures("[[figure:glyph-outline-slash-vs-yen]]")

        self.assertEqual(rendered.count("<svg"), 2)
        self.assertIn("U+002F", rendered)
        self.assertIn("U+005C", rendered)
        self.assertNotIn("<button", rendered)
        self.assertNotIn("aria-pressed", rendered)

    def test_svg_figures_carry_an_accessible_name(self):
        rendered = figures("[[figure:glyph-outline-slash-vs-yen]]")

        self.assertEqual(rendered.count('role="img"'), 2)
        self.assertEqual(rendered.count("aria-label"), 2)

    def test_the_nixie_green_is_the_one_documented_exception(self):
        """
        A prop, not a piece of interface — a tube glows the same colour in both
        themes. The hex lives in post-body.css, not in the partial.
        """
        rendered = figures("[[figure:divergence-meter]]")

        self.assertIn("fig-nixie", rendered)
        self.assertNotIn("#3fbf6f", rendered)


class PostPageFigureTests(TestCase):
    """The filter as the post page actually uses it, end to end."""

    def setUp(self):
        self.owner = User.objects.create_user("author", password="pw")
        self.post = Post.objects.create(
            title="Post With A Figure",
            content="<p>lede</p>\n[[figure:ms-ui-gothic-widths]]\n<p>after</p>",
            owner=self.owner,
        )

    def test_the_token_is_expanded_in_the_rendered_page(self):
        response = self.client.get(reverse("website_app:post", args=[self.post.slug]))

        self.assertNotContains(response, "[[figure:")
        self.assertContains(response, "fig-bar-fill")

    def test_the_post_page_loads_the_figure_stylesheet(self):
        """
        Figure chrome and the post-body prose classes are only ever needed here,
        so they are not folded into style.css — but the file must actually be
        linked, or every figure renders unstyled.
        """
        response = self.client.get(reverse("website_app:post", args=[self.post.slug]))

        self.assertContains(response, "post-body")

    def test_the_blog_list_does_not_load_it(self):
        response = self.client.get(reverse("website_app:blog"))

        self.assertNotContains(response, "post-body")

    def test_a_body_with_a_token_is_still_ordinary_prose_for_the_excerpt(self):
        """
        A token is text, so strip_tags leaves it alone. Without strip_figures the
        literal `[[figure:ms-ui-gothic-widths]]` opened the RSS summary and the
        meta description — which is how this was caught.
        """
        excerpt = self.post.excerpt()

        self.assertNotIn("[[figure:", excerpt)
        self.assertEqual(excerpt, "lede after")

    def test_the_token_does_not_reach_the_page_metadata(self):
        response = self.client.get(reverse("website_app:post", args=[self.post.slug]))

        self.assertNotContains(response, "[[figure:")

    def test_the_token_does_not_reach_the_feed(self):
        response = self.client.get(reverse("website_app:feed"))

        self.assertNotContains(response, "[[figure:")


class PlainTextTests(TestCase):
    """
    Covers website_app/post_text.py, the one pipeline behind Post.excerpt, the
    RSS summary, the meta description and the --diff fingerprint. Each case here
    is a bug that reached a live page or a misleading tool output.
    """

    def test_a_comment_naming_a_tag_does_not_eat_the_prose(self):
        """
        The one that shipped. _NON_PROSE pairs an opening style tag with a
        closing one by regex, so a comment that merely *named* the tag paired
        with the real closing tag below, the comment lost its terminator, and
        everything up to the next one vanished — including the lede.
        """
        body = (
            "<!-- note to self: do not put a <style> tag in a comment -->\n"
            "<p>The lede survives.</p>\n"
            "<style>.fx { color: red; }</style>\n"
            "<p>So does the rest.</p>"
        )

        self.assertEqual(plain_text(body), "The lede survives. So does the rest.")

    def test_adjacent_blocks_do_not_run_together(self):
        self.assertEqual(plain_text("<p>one</p><p>two</p>"), "one two")

    def test_table_cells_do_not_run_together(self):
        """
        Caught by --diff: the delivery table read as `deliverytotal sizerequests`
        from the file and correctly from the database, purely because TinyMCE had
        put the cells on separate lines.
        """
        body = '<tr><th>delivery</th><th class="num">total size</th><th>risk</th></tr>'

        self.assertEqual(plain_text(body), "delivery total size risk")

    def test_inline_tags_do_not_add_space_before_punctuation(self):
        """The other direction: a blanket tag-to-space rule breaks this."""
        self.assertEqual(
            plain_text("<p>Some <strong>markup</strong>.</p>"), "Some markup."
        )

    def test_style_and_script_contents_are_not_prose(self):
        body = "<style>.a { color: red }</style><p>Words.</p><script>x = 1;</script>"

        self.assertEqual(plain_text(body), "Words.")

    def test_entities_are_unescaped_once(self):
        self.assertEqual(plain_text("<p>a&nbsp;b &amp; c</p>"), "a b & c")

    def test_figure_tokens_are_removed_when_a_stripper_is_given(self):
        body = "<p>before</p>[[figure:ms-ui-gothic-widths]]<p>after</p>"

        self.assertEqual(plain_text(body, strip_tokens=strip_figures), "before after")
        self.assertIn("[[figure:", plain_text(body))

    def test_empty_input(self):
        self.assertEqual(plain_text(""), "")
        self.assertEqual(plain_text(None), "")


class FingerprintTests(TestCase):
    """
    Covers the comparison behind `publish_post.py --diff`. Byte equality was the
    wrong question: TinyMCE rewrites line endings, re-encodes punctuation as
    entities and collapses blank lines on every Save, so a byte diff cried wolf
    in exactly the situation the tool exists for.
    """

    BODY = (
        '<p class="post-lede">Lede — with punctuation.</p>\n'
        "[[figure:ms-ui-gothic-widths]]\n"
        '<div class="post-note">A <b>note</b>.</div>\n'
        "<pre><code>code</code></pre>"
    )

    def test_the_editors_cosmetic_rewrites_do_not_change_the_fingerprint(self):
        saved = (
            self.BODY.replace("\n", "\r\n")
            .replace("—", "&mdash;")
            .replace("<b>", "<strong>")
            .replace("</b>", "</strong>")
        )

        self.assertNotEqual(saved, self.BODY)
        self.assertEqual(fingerprint(saved), fingerprint(self.BODY))

    def test_a_lost_figure_token_changes_the_fingerprint(self):
        mangled = self.BODY.replace("[[figure:ms-ui-gothic-widths]]", "")

        self.assertNotEqual(fingerprint(mangled), fingerprint(self.BODY))
        self.assertEqual(fingerprint(mangled)["figures"], [])

    def test_a_lost_class_changes_the_fingerprint(self):
        mangled = self.BODY.replace(' class="post-note"', "")

        self.assertNotEqual(fingerprint(mangled), fingerprint(self.BODY))
        self.assertNotIn("post-note", fingerprint(mangled)["classes"])

    def test_a_stripped_code_block_changes_the_fingerprint(self):
        mangled = self.BODY.replace("<pre><code>code</code></pre>", "<p>code</p>")

        self.assertEqual(fingerprint(self.BODY)["tags"]["pre"], 1)
        self.assertEqual(fingerprint(mangled)["tags"]["pre"], 0)

    def test_a_stripped_style_block_changes_the_fingerprint(self):
        """What TinyMCE actually did to the live post."""
        with_style = "<style>.fx { color: red }</style>" + self.BODY

        self.assertEqual(fingerprint(with_style)["tags"]["style"], 1)
        self.assertEqual(fingerprint(self.BODY)["tags"]["style"], 0)

    def test_changed_prose_changes_the_fingerprint(self):
        mangled = self.BODY.replace("Lede", "Something else")

        self.assertNotEqual(
            fingerprint(mangled)["prose"], fingerprint(self.BODY)["prose"]
        )


class PostAdminRawHtmlTests(TestCase):
    """
    Covers the one thing standing between a rich post body and the database:
    the admin's `content` widget.

    `Post.content` is a django-tinymce `HTMLField`, which is a plain TextField
    plus a widget — nothing is sanitised on save, and post.html renders it
    through the `figures` filter, which marks it safe. So bodies published by
    scripts/publish_post.py keep their inline
    <style>, <svg> and <script>, and the only thing that destroys them is the
    editor rewriting the field in the browser. `raw_html` turns the editor off.

    Note what these tests can and cannot show: the mangling itself is
    client-side, so no Django test can reproduce it. What is asserted here is
    that the widget is swapped, that the swap is per-object, and that a full
    admin round trip returns the body byte for byte.
    """

    RAW_BODY = (
        "<style>.fx { color: var(--accent); }</style>\n"
        '<div class="fx"><p>prose</p>\n'
        '<svg viewBox="0 0 10 10"><polygon points="0,0 10,0 10,10"/></svg></div>\n'
        '<script>(function () { if (1 < 2) console.log("x"); })();</script>'
    )

    def setUp(self):
        self.owner = User.objects.create_superuser("author", password="pw")
        self.raw = Post.objects.create(
            title="Raw body post",
            content=self.RAW_BODY,
            owner=self.owner,
            raw_html=True,
        )
        self.rich = Post.objects.create(
            title="Ordinary post", content="<p>hi</p>", owner=self.owner
        )
        self.admin = PostAdmin(Post, site)
        self.request = RequestFactory().get("/")
        self.request.user = self.owner

    def _content_widget(self, obj):
        form = self.admin.get_form(self.request, obj)
        return form.base_fields["content"].widget

    def test_raw_post_is_edited_as_source_not_in_the_editor(self):
        widget = self._content_widget(self.raw)

        self.assertNotIsInstance(widget, TinyMCE)
        self.assertIsInstance(widget, forms.Textarea)

    def test_ordinary_post_still_gets_the_rich_text_editor(self):
        self.assertIsInstance(self._content_widget(self.rich), TinyMCE)

    def test_the_add_form_gets_the_rich_text_editor(self):
        """obj is None on the add view, so there is no flag to read yet."""
        self.assertIsInstance(self._content_widget(None), TinyMCE)

    def test_the_swap_does_not_leak_between_objects(self):
        """
        The widget is replaced on the form class, so a leak would silently turn
        the editor off site-wide. ModelAdmin builds a fresh class per call.
        """
        self._content_widget(self.raw)

        self.assertIsInstance(self._content_widget(self.rich), TinyMCE)

    def test_raw_field_explains_why_the_editor_is_off(self):
        form = self.admin.get_form(self.request, self.raw)
        help_text = form.base_fields["content"].help_text

        self.assertIn("Raw HTML", help_text)
        self.assertIn("publish_post.py", help_text)

    def test_saving_a_raw_post_through_the_admin_keeps_the_body_verbatim(self):
        """
        The regression this whole flag exists to prevent: opening a published
        post in the admin and pressing Save used to come back with the demos
        gone. Nothing server-side rewrites the body, so an unchanged POST must
        round-trip byte for byte.
        """
        self.client.force_login(self.owner)
        url = reverse("admin:website_app_post_change", args=[self.raw.pk])

        response = self.client.post(
            url,
            {
                "title": self.raw.title,
                "content": self.RAW_BODY,
                "raw_html": "on",
                "slug": self.raw.slug,
                "owner": self.owner.pk,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.raw.refresh_from_db()
        self.assertEqual(self.raw.content, self.RAW_BODY)
        self.assertTrue(self.raw.raw_html)

    def test_editing_the_title_in_the_admin_does_not_move_the_url(self):
        """
        The second trap of the same family as the widget one: publish_post.py
        hands out slugs that do not match the title, so re-deriving on save
        would break every inbound link on the first copy edit.
        """
        self.client.force_login(self.owner)
        Post.objects.filter(pk=self.raw.pk).update(slug="arpa-domain")
        url = reverse("admin:website_app_post_change", args=[self.raw.pk])

        response = self.client.post(
            url,
            {
                "title": "A completely different title",
                "content": self.RAW_BODY,
                "raw_html": "on",
                "slug": "arpa-domain",
                "owner": self.owner.pk,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.raw.refresh_from_db()
        self.assertEqual(self.raw.slug, "arpa-domain")
        self.assertEqual(self.raw.title, "A completely different title")

    def test_a_raw_body_reaches_the_page_unescaped(self):
        """The other half of the contract: post.html renders content |safe."""
        response = self.client.get(reverse("website_app:post", args=[self.raw.slug]))

        self.assertContains(response, "<style>.fx { color: var(--accent); }</style>")
        self.assertContains(response, "<polygon")
        self.assertContains(response, "<script>(function () {")

    def test_raw_html_defaults_to_off(self):
        """New posts written through the admin are ordinary rich-text posts."""
        self.assertFalse(self.rich.raw_html)


class RawHtmlBackfillTests(TestCase):
    """
    Migration 0011 flags the posts that were already published before the flag
    existed. Without the backfill the trap stays armed on exactly the posts
    that cannot survive it, so the predicate is worth pinning down.

    `Post.body_needs_raw_html` is the runtime twin, used by publish_post.py to
    set the flag from the body rather than by hand. The migration keeps its own
    frozen copy so that editing the model cannot change what an already-applied
    migration meant — these tests hold the two in step.
    """

    BODIES_NEEDING_RAW = (
        "<style>.fx {}</style><p>x</p>",
        "<p>x</p><script>1</script>",
        '<svg viewBox="0 0 1 1"></svg>',
        "<P>x</P><SCRIPT>1</SCRIPT>",
    )

    ORDINARY_BODIES = (
        "<p>just words</p>",
        '<p><img src="/media/media_files/nvim.webp" alt=""></p>',
        "<h2>Heading</h2><ul><li>item</li></ul>",
        '<p>prose</p>[[figure:ms-ui-gothic-widths]]<div class="post-note">x</div>',
        "",
        None,
    )

    def test_bodies_the_editor_cannot_represent_are_flagged(self):
        for body in self.BODIES_NEEDING_RAW:
            with self.subTest(body=body):
                self.assertTrue(needs_raw_html(body))

    def test_ordinary_prose_is_left_alone(self):
        for body in self.ORDINARY_BODIES:
            with self.subTest(body=body):
                self.assertFalse(needs_raw_html(body))

    def test_the_runtime_predicate_agrees_with_the_migration(self):
        for body in self.BODIES_NEEDING_RAW + self.ORDINARY_BODIES:
            with self.subTest(body=body):
                self.assertEqual(Post.body_needs_raw_html(body), needs_raw_html(body))

    def test_a_token_only_body_needs_no_raw_flag(self):
        """
        Which is the whole point of the figure mechanism: once the diagrams are
        tokens, the body is prose and the rich-text editor is safe again.
        """
        body = (
            '<p class="post-lede">lede</p>\n'
            "[[figure:ms-ui-gothic-widths]]\n"
            '<div class="post-note">a note</div>\n'
            '<table class="post-table"><tr><td class="num">1</td></tr></table>'
        )

        self.assertFalse(Post.body_needs_raw_html(body))

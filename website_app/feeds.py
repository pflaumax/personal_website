"""RSS feed for the blog.

Uses django.contrib.syndication from the standard Django distribution — no new
dependency, nothing to add to INSTALLED_APPS.
"""

from datetime import datetime, time

from django.contrib.syndication.views import Feed
from django.urls import reverse
from django.utils import timezone
from django.utils.feedgenerator import Rss201rev2Feed

from .models import Post


class BrowsableRssFeed(Rss201rev2Feed):
    """RSS served as application/xml rather than application/rss+xml.

    Both are valid and readers accept either, but browsers have no renderer for
    application/rss+xml, so clicking the link downloads a file instead of
    showing the feed. application/xml gets the browser's built-in XML view,
    which is what every hand-rolled feed on the web does.
    """

    content_type = "application/xml; charset=utf-8"


class LatestPostsFeed(Feed):
    """The most recent posts, newest first."""

    feed_type = BrowsableRssFeed
    title = "Max Pflaum"
    description = "Posts by Max Pflaum — software development, tooling, hardware."
    link = "/blog/"

    # Enough to fill a reader without turning the feed into the whole archive.
    LIMIT = 20
    def items(self):
        return Post.objects.all()[: self.LIMIT]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        # Trimmed rather than sent whole: the body is TinyMCE HTML carrying
        # inline styles and pasted markup, which renders unpredictably in feed
        # readers. Post.excerpt also handles the entity double-escape trap.
        return item.excerpt()

    def item_link(self, item):
        return item.get_absolute_url()

    def item_pubdate(self, item):
        """Convert the post's date to an aware datetime.

        Post.date_added is a DateField, but RSS pubDate needs a datetime — and
        Django warns (or the value is read as naive) unless it carries a
        timezone. Midnight in the active timezone is the honest reading of a
        date-only value.
        """
        return timezone.make_aware(datetime.combine(item.date_added, time.min))

    def feed_url(self):
        return reverse("website_app:feed")

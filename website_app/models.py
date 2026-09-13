import html
import logging
import re

from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse
from django.utils.html import strip_tags
from django.utils.text import slugify
from tinymce.models import HTMLField

from .figures import strip_figures

logger = logging.getLogger(__name__)


class MediaFile(models.Model):
    """Model for storing media files uploaded by users."""

    # Limited to what TinyMCE actually wires up (see TINYMCE_DEFAULT_CONFIG's
    # image_list/media_list) — there is no upload path for video/document.
    MEDIA_TYPE_CHOICES = (
        ("image", "Image"),
        ("audio", "Audio"),
    )

    title = models.CharField(max_length=200)
    file_type = models.CharField(
        max_length=10, choices=MEDIA_TYPE_CHOICES, default="image"
    )
    # No storage= argument on purpose: STORAGES["default"] in settings.py is the
    # only thing that decides the backend. This was once a custom S3FileField
    # that bound S3Boto3Storage at import time — a second, competing mechanism.
    file = models.FileField(upload_to="media_files/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        """Return a readable representation of the media file."""
        return f"{self.title} ({self.get_file_type_display()})"  # type: ignore

    @property
    def file_url(self):
        """Return the URL of the uploaded file."""
        return self.file.url

    def save(self, *args, **kwargs):
        """Save the uploaded file."""
        super().save(*args, **kwargs)

        if not self.file:
            logger.debug("Saved MediaFile %r without a file", self.title)
            return

        try:
            logger.debug(
                "Saved MediaFile %r: storage=%s, url=%s, name=%s",
                self.title,
                self.file.storage.__class__.__name__,
                self.file.url,
                self.file.name,
            )
        except Exception:
            logger.exception(
                "Could not resolve file details for MediaFile %r", self.title
            )


class Post(models.Model):
    """
    Model representing a blog post.
    Includes automatic slug generation and uniqueness check.
    """

    title = models.CharField(max_length=200)
    content = HTMLField()
    # Posts whose body carries inline <style>, <svg> or <script> cannot survive
    # a round trip through TinyMCE: its default allowlist has none of those
    # elements, and it rewrites the body when the form *loads*, so merely
    # opening such a post and pressing Save destroys it. This flag tells the
    # admin to edit the field as source text instead. See PostAdmin.get_form.
    raw_html = models.BooleanField(
        default=False,
        verbose_name="edit as raw HTML",
        help_text=(
            "The body contains inline style, SVG or script that TinyMCE would "
            "strip. Edit it as source text instead of in the rich-text editor."
        ),
    )
    date_added = models.DateField(auto_now_add=True)
    slug = models.SlugField(unique=True, blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        ordering = ["-date_added"]

    def __str__(self):
        """Return the title of the post."""
        return self.title

    # Long enough for a feed summary; the meta-description variant trims harder.
    EXCERPT_LENGTH = 320
    META_DESCRIPTION_LENGTH = 155

    # Elements TinyMCE's default allowlist has nothing for. A body containing
    # one of these cannot be opened in the rich-text editor without being
    # rewritten, which is what `raw_html` exists to prevent.
    #
    # Migration 0011 carries its own frozen copy of this list on purpose: an
    # applied migration must not change meaning when this one is edited.
    RAW_MARKERS = ("<style", "<script", "<svg")

    @classmethod
    def body_needs_raw_html(cls, content):
        """True if `content` would not survive a round trip through TinyMCE."""
        lowered = (content or "").lower()
        return any(marker in lowered for marker in cls.RAW_MARKERS)

    # strip_tags drops the tags but keeps whatever sits between them, so a post
    # carrying an inline <style> or <script> block would otherwise open its
    # excerpt — and its RSS summary, and its meta description — with raw CSS.
    _NON_PROSE = re.compile(r"<(style|script)\b[^>]*>.*?</\1\s*>", re.I | re.S)

    def excerpt(self, length=None):
        """Plain-text opening of the post.

        strip_tags removes tags but leaves entities, so unescape once here —
        otherwise a stored `&nbsp;` survives as literal text and whatever
        renders it escapes the ampersand again, so readers see `&amp;nbsp;`.

        Figure tokens go first: they are plain text, so strip_tags has nothing
        to remove and a literal `[[figure:name]]` would otherwise open the RSS
        summary and the meta description.
        """
        limit = self.EXCERPT_LENGTH if length is None else length
        body = self._NON_PROSE.sub(" ", strip_figures(self.content))
        text = " ".join(html.unescape(strip_tags(body)).split())
        if len(text) <= limit:
            return text
        return text[:limit].rsplit(" ", 1)[0] + "…"

    @property
    def meta_description(self):
        """Shorter excerpt, sized for a <meta name="description">."""
        return self.excerpt(self.META_DESCRIPTION_LENGTH)

    def get_absolute_url(self):
        """Return the canonical URL for this post.

        The syndication framework builds item links from this, and it is the
        single place the post URL shape is written down.
        """
        return reverse("website_app:post", kwargs={"slug": self.slug})

    def save(self, *args, **kwargs):
        """Derive the slug on the first save only, so permalinks stay put.

        The slug used to be re-derived whenever the title changed. That quietly
        moved a published post's URL, and it was worse for posts whose slug was
        chosen by hand (scripts/publish_post.py): `/blog/arpa-domain/` would
        have become the whole title, slugified, on the first typo fix in the
        admin. A title is editable copy; a URL is a promise.

        The slug field is editable and `blank=True`, so a deliberate rename is
        still possible — type a new one, or clear the field to ask for a fresh
        one derived from the current title.
        """
        if not self.slug:
            self.slug = self.get_unique_slug(slugify(self.title))
        super().save(*args, **kwargs)

    def get_unique_slug(self, base_slug):
        """Generate a unique slug by adding a number suffix if necessary."""
        slug = base_slug
        counter = 1
        while Post.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug

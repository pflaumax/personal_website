import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils.text import slugify
from storages.backends.s3boto3 import S3Boto3Storage
from tinymce.models import HTMLField

logger = logging.getLogger(__name__)


class S3FileField(models.FileField):
    """Custom FileField that uses S3 storage if USE_S3 is set in settings."""

    def __init__(self, *args, **kwargs):
        if getattr(settings, "USE_S3", False):
            kwargs["storage"] = S3Boto3Storage()
        super().__init__(*args, **kwargs)


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
    file = S3FileField(upload_to="media_files/")
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
    date_added = models.DateField(auto_now_add=True)
    slug = models.SlugField(unique=True, blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        ordering = ["-date_added"]

    def __str__(self):
        """Return the title of the post."""
        return self.title

    def save(self, *args, **kwargs):
        """
        Generate a unique slug on save, only if title is new or has changed.
        """
        if not self.slug or self.title_has_changed():
            new_slug = slugify(self.title)
            self.slug = self.get_unique_slug(new_slug)
        super().save(*args, **kwargs)

    def title_has_changed(self):
        """Check if the title has changed for existing posts."""
        if self.pk:
            original = Post.objects.get(pk=self.pk)
            return original.title != self.title
        return True  # For new post always generate slug

    def get_unique_slug(self, base_slug):
        """Generate a unique slug by adding a number suffix if necessary."""
        slug = base_slug
        counter = 1
        while Post.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug

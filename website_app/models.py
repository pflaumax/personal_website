from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import User
from tinymce.models import HTMLField


class MediaFile(models.Model):
    """Model for storing various media files"""

    MEDIA_TYPE_CHOICES = (
        ("image", "Image"),
        ("audio", "Audio"),
        ("video", "Video"),
        ("document", "Document"),
    )
    title = models.CharField(max_length=200)
    file_type = models.CharField(
        max_length=10, choices=MEDIA_TYPE_CHOICES, default="image"
    )
    file = models.FileField(upload_to="media_files/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.get_file_type_display()})"

    @property
    def file_url(self):
        return self.file.url

    def save(self, *args, **kwargs):
        from django.conf import settings
        import logging

        logger = logging.getLogger(__name__)

        # Log before save
        logger.info("--- Attempting to save MediaFile ---")
        logger.info(f"Current DEFAULT_FILE_STORAGE: {settings.DEFAULT_FILE_STORAGE}")
        logger.info(f"USE_S3 setting: {getattr(settings, 'USE_S3', 'Not defined')}")
        logger.info(f"File field before save: {self.file}")

        try:
            super().save(*args, **kwargs)
            logger.info(f"File successfully saved")
        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            logger.exception("Exception details:")
            raise  # Re-raise exception after logging

        # Log after save
        logger.info(f"File field after save: {self.file}")
        try:
            if self.file:
                logger.info(f"Generated URL: {self.file.url}")
                logger.info(f"File storage: {self.file.storage}")
                logger.info(f"File name: {self.file.name}")
        except Exception as e:
            logger.error(f"Error getting file details: {str(e)}")

        logger.info("--- Finished saving MediaFile ---")


class Post(models.Model):
    """Model representing a blog post."""

    title = models.CharField(max_length=200)
    content = HTMLField()
    excerpt = models.TextField(
        blank=True, max_length=300, help_text="Short description for list view"
    )
    date_added = models.DateField(auto_now_add=True)
    slug = models.SlugField(unique=True, blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        ordering = ["-date_added"]

    def save(self, *args, **kwargs):
        """Slug generation and duplicate handling."""
        if not self.slug or self.title_has_changed():
            new_slug = slugify(self.title)
            self.slug = self.get_unique_slug(new_slug)
        super().save(*args, **kwargs)

    def title_has_changed(self):
        """Check if the title has changed for existing posts."""
        if self.pk:  # Primary key
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

    def __str__(self):
        """Return a string representation of the model."""
        return self.title

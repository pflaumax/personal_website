from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import User
from tinymce.models import HTMLField
from django.core.files.storage import default_storage
from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage
import os


class S3FileField(models.FileField):
    def __init__(self, *args, **kwargs):
        if getattr(settings, "USE_S3", False):
            kwargs["storage"] = S3Boto3Storage()
        super().__init__(*args, **kwargs)


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
    # Use our custom S3FileField instead of models.FileField
    file = S3FileField(upload_to="media_files/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.get_file_type_display()})"

    @property
    def file_url(self):
        return self.file.url

    def save(self, *args, **kwargs):
        from django.conf import settings

        print("\n--- Attempting to save MediaFile ---")
        print(f"Current DEFAULT_FILE_STORAGE: {settings.DEFAULT_FILE_STORAGE}")
        print(f"USE_S3 setting: {getattr(settings, 'USE_S3', 'Not defined')}")
        print(f"File field before save: {self.file}")
        print(f"Storage class for model: {self.file.storage.__class__.__name__}")

        try:
            super().save(*args, **kwargs)
            print(f"File successfully saved")
        except Exception as e:
            print(f"Error saving file: {str(e)}")
            import traceback

            print(traceback.format_exc())
            raise

        print(f"File field after save: {self.file}")
        try:
            if self.file:
                print(f"Generated URL: {self.file.url}")
                print(f"File storage: {self.file.storage.__class__.__name__}")
                print(f"File name: {self.file.name}")
        except Exception as e:
            print(f"Error getting file details: {str(e)}")

        print("--- Finished saving MediaFile ---\n")


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

from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import User
from tinymce.models import HTMLField
from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage


# Define storage explicitly for this model
s3_storage = S3Boto3Storage() if getattr(settings, "USE_S3", False) else None


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
    file = models.FileField(upload_to="media_files/", storage=s3_storage)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.get_file_type_display()})"

    @property
    def file_url(self):
        return self.file.url

    def save(self, *args, **kwargs):
        from django.conf import settings
        from storages.backends.s3boto3 import S3Boto3Storage

        print("\n--- Attempting to save MediaFile ---")
        print(f"Current DEFAULT_FILE_STORAGE: {settings.DEFAULT_FILE_STORAGE}")
        print(f"USE_S3 setting: {getattr(settings, 'USE_S3', 'Not defined')}")
        print(f"File field before save: {self.file}")

        # Check storage class before save
        storage_class = (
            self.file.storage.__class__.__name__
            if hasattr(self.file, "storage")
            else "Unknown"
        )
        print(f"Storage class for model: {storage_class}")

        # Ensure we're using S3 storage if configured
        if getattr(settings, "USE_S3", False) and not isinstance(
            self.file.storage, S3Boto3Storage
        ):
            print("Warning: File storage is not S3Boto3Storage, attempting to fix...")
            from storages.backends.s3boto3 import S3Boto3Storage

            if not hasattr(self, "_file_obj") and hasattr(self.file, "file"):
                self._file_obj = self.file.file
            self.file.storage = S3Boto3Storage()
            if hasattr(self, "_file_obj"):
                self.file.file = self._file_obj

        try:
            super().save(*args, **kwargs)
            print(f"File successfully saved")
        except Exception as e:
            print(f"Error saving file: {str(e)}")
            import traceback

            print(traceback.format_exc())
            raise


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

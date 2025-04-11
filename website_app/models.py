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
        return f"{self.title} ({self.get_file_type_display()})"  # type: ignore

    @property
    def file_url(self):
        return self.file.url


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

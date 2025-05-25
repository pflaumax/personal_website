from django.contrib import admin
from .models import Post, MediaFile


class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "date_added", "owner")
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ["title", "content"]


class MediaFileAdmin(admin.ModelAdmin):
    list_display = ("title", "file_type", "file", "file_size", "uploaded_at")
    list_filter = ("file_type", "uploaded_at")
    search_fields = ["title"]


admin.site.register(Post, PostAdmin)
admin.site.register(MediaFile, MediaFileAdmin)

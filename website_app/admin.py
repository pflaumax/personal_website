from django import forms
from django.contrib import admin
from django.utils.html import format_html

from .models import MediaFile, Post


class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "date_added", "owner", "raw_html")
    list_filter = ("raw_html",)
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ["title", "content"]

    def get_form(self, request, obj=None, **kwargs):
        """Swap TinyMCE for a plain source textarea on raw-HTML posts.

        `Post.content` is a django-tinymce `HTMLField`, which only means "use
        the TinyMCE widget in forms" — the field itself stores and returns text
        untouched, and post.html renders it with `|safe`. So the editor is the
        single thing standing between a rich body and the database, and turning
        it off is enough to make the admin non-destructive.

        The swap has to happen here rather than through `formfield_overrides`,
        which keys on the field class and so cannot vary per object. Django
        builds a fresh form class per call via `modelform_factory`, so mutating
        `base_fields` does not leak into other requests.
        """
        form = super().get_form(request, obj, **kwargs)
        if obj is not None and obj.raw_html:
            # A plain forms.Textarea, not admin_widgets.AdminTextareaWidget:
            # HTMLField.formfield() explicitly turns the latter back into
            # TinyMCE, which would undo the whole point.
            form.base_fields["content"].widget = forms.Textarea(
                attrs={
                    "rows": 30,
                    "spellcheck": "false",
                    "autocapitalize": "off",
                    "autocorrect": "off",
                    "style": (
                        "width: 100%; font-family: ui-monospace, SFMono-Regular, "
                        "Menlo, monospace; font-size: 12px; line-height: 1.5;"
                    ),
                }
            )
            form.base_fields["content"].help_text = format_html(
                "Raw HTML — served verbatim, nothing is sanitised on the way "
                "out. The rich-text editor is off for this post on purpose: it "
                "would strip the inline <code>&lt;style&gt;</code>, "
                "<code>&lt;svg&gt;</code> and <code>&lt;script&gt;</code>. "
                "If this post has a source file under "
                "<code>media_for_blogposts/</code> (which is gitignored, so "
                "that file is the only copy), that file is the source of truth "
                "— edit it and re-run <code>scripts/publish_post.py</code> "
                "instead, or the two will diverge silently."
            )
        return form


class MediaFileAdmin(admin.ModelAdmin):
    list_display = ("title", "file_type", "file", "uploaded_at")
    list_filter = ("file_type", "uploaded_at")
    search_fields = ["title"]


admin.site.register(Post, PostAdmin)
admin.site.register(MediaFile, MediaFileAdmin)

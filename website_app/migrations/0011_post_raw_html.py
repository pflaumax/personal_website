"""Add Post.raw_html and set it on the posts that already need it.

Bodies published by scripts/publish_post.py carry inline <style>, <svg> and
<script>. TinyMCE's default allowlist has none of those, so the flag has to be
on before anyone opens those posts in the admin — otherwise the migration
closes the trap for future posts only and leaves the existing ones armed.
"""

from django.db import migrations, models

# Substrings that mean "TinyMCE cannot represent this body".
RAW_MARKERS = ("<style", "<script", "<svg")


def needs_raw_html(content):
    """True if this body would not survive a round trip through the editor."""
    lowered = (content or "").lower()
    return any(marker in lowered for marker in RAW_MARKERS)


def flag_existing_raw_posts(apps, schema_editor):
    Post = apps.get_model("website_app", "Post")
    for post in Post.objects.all().only("pk", "content"):
        if needs_raw_html(post.content):
            Post.objects.filter(pk=post.pk).update(raw_html=True)


def unflag(apps, schema_editor):
    """Reverse leg: the column is dropped anyway, so nothing to undo."""


class Migration(migrations.Migration):
    dependencies = [
        ("website_app", "0010_alter_mediafile_file_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="post",
            name="raw_html",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "The body contains inline style, SVG or script that TinyMCE "
                    "would strip. Edit it as source text instead of in the "
                    "rich-text editor."
                ),
                verbose_name="edit as raw HTML",
            ),
        ),
        migrations.RunPython(flag_existing_raw_posts, unflag),
    ]

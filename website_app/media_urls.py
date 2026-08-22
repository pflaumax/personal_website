"""
Rewrite absolute S3 media URLs embedded in Post.content to site-relative paths.

The bucket these URLs pointed at was deleted, so every such reference renders as
a broken image. The files now live on local disk under MEDIA_ROOT and are served
at MEDIA_URL, so the absolute prefix simply becomes "/media/".

LEGACY_S3_MEDIA_PREFIX is a hardcoded literal on purpose. This is a historical
cleanup of rows written while USE_S3 was on; deriving the prefix from settings
would make the command a silent no-op the moment those S3 settings are removed
— which is exactly what happens next. Same reasoning as stats/purge.py.
"""

LEGACY_S3_MEDIA_PREFIX = "https://pflaumax-media.s3.eu-north-1.amazonaws.com/media/"

LOCAL_MEDIA_PREFIX = "/media/"


def rewrite_content(content, legacy_prefix=LEGACY_S3_MEDIA_PREFIX, media_prefix=LOCAL_MEDIA_PREFIX):
    """
    Return (new_content, replacements_made).

    Idempotent: once the legacy prefix is gone, further runs replace nothing.
    """
    if not content:
        return content, 0

    replacements = content.count(legacy_prefix)
    if not replacements:
        return content, 0

    return content.replace(legacy_prefix, media_prefix), replacements


def rewrite_posts(
    post_model,
    legacy_prefix=LEGACY_S3_MEDIA_PREFIX,
    media_prefix=LOCAL_MEDIA_PREFIX,
    commit=True,
):
    """
    Rewrite every post body containing the legacy prefix.

    Returns a list of (slug, replacements) for the posts that changed. Writes via
    queryset.update() rather than instance.save() so the slug-regeneration logic
    in Post.save() is never involved — only content is touched.
    """
    changed = []

    for post in post_model.objects.all():
        new_content, replacements = rewrite_content(
            post.content, legacy_prefix, media_prefix
        )
        if not replacements:
            continue

        changed.append((post.slug, replacements))
        if commit:
            post_model.objects.filter(pk=post.pk).update(content=new_content)

    return changed

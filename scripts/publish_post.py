"""Publish a post body straight into the database, bypassing the TinyMCE form.

`Post.content` is a django-tinymce `HTMLField` and `post.html` renders it with
`|safe`, so whatever reaches the column is served verbatim — inline `<style>`,
inline `<svg>` filter defs and inline `<script>` all work. What does *not*
survive is the admin editor: TinyMCE strips `<script>` and mangles `<svg>` on
save. This writes the column directly instead.

    python scripts/publish_post.py <slug> <title> <path/to/body.html>
    python scripts/publish_post.py --show <slug>

Re-running with the same slug updates the body in place and leaves the slug and
`date_added` alone, so the post keeps its URL and its position in the feed.

WARNING: opening this post in the Django admin and pressing Save will run the
body back through TinyMCE and destroy the demos. Edit the source file and
re-run this script instead.
"""

import os
import sys

import django
from dotenv import load_dotenv

# Add the project root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

# Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "website_project.settings")
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402

from website_app.models import Post  # noqa: E402

User = get_user_model()


def _owner():
    """The account posts are attributed to: the first superuser."""
    owner = User.objects.filter(is_superuser=True).order_by("pk").first()
    if owner is None:
        sys.exit("No superuser exists; run scripts/create_superuser.py first.")
    return owner


def show(slug):
    """Print what is currently stored, to confirm nothing has been mangled."""
    post = Post.objects.filter(slug=slug).first()
    if post is None:
        sys.exit(f"No post with slug {slug!r}.")

    body = post.content
    print(f"{post.title}  ({post.date_added}, {len(body)} chars)")
    for tag in ("<script", "<svg", "<style", "<filter", "data-toggle"):
        print(f"  {tag:<14} x{body.count(tag)}")


def publish(slug, title, path):
    with open(path, encoding="utf-8") as fh:
        body = fh.read()

    post = Post.objects.filter(slug=slug).first()
    if post is None:
        # Post.save() derives a slug from the title, so set it afterwards to
        # keep the one asked for rather than the generated one.
        post = Post(title=title, content=body, owner=_owner())
        post.save()
        Post.objects.filter(pk=post.pk).update(slug=slug)
        print(f"Created {slug!r} ({len(body)} chars).")
    else:
        # update() skips save(), so the slug is never re-derived from the title.
        Post.objects.filter(pk=post.pk).update(title=title, content=body)
        print(f"Updated {slug!r} ({len(body)} chars).")

    print(f"  /blog/{slug}/")


def main():
    args = sys.argv[1:]
    if len(args) == 2 and args[0] == "--show":
        show(args[1])
    elif len(args) == 3:
        publish(args[0], args[1], args[2])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()

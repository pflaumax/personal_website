"""Publish a post body straight into the database from a file on disk.

`Post.content` is a django-tinymce `HTMLField`, which stores text untouched, and
post.html renders it through the `figures` filter, which marks it safe. So
whatever reaches the column is served verbatim. This writes the column directly,
which is the only way to get a body carrying inline `<style>`, `<svg>` or
`<script>` past the admin form — TinyMCE's default allowlist has no elements for
any of them.

    python scripts/publish_post.py <slug> <title> <path/to/body.html>
    python scripts/publish_post.py --show <slug>
    python scripts/publish_post.py --diff <slug> <path/to/body.html>

Re-running with the same slug updates the body in place and leaves the slug and
`date_added` alone, so the post keeps its URL and its position in the feed.

`raw_html` is set from the body itself: a body that still contains an inline
style, script or svg block gets the plain source textarea in the admin, and one
that does not gets the rich-text editor back. Bodies built out of
`[[figure:name]]` tokens (see website_app/figures.py) fall in the second group.

The source file stays the source of truth either way — `media_for_blogposts/` is
gitignored, so it is also the only copy. `--diff` reports whether the database
still matches it, which is how you check whether something (an admin Save, say)
has rewritten the stored body.
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


def _get(slug):
    post = Post.objects.filter(slug=slug).first()
    if post is None:
        sys.exit(f"No post with slug {slug!r}.")
    return post


def show(slug):
    """Print what is currently stored, to confirm nothing has been mangled."""
    post = _get(slug)
    body = post.content

    print(f"{post.title}  ({post.date_added}, {len(body)} chars)")
    print(f"  raw_html       {post.raw_html}")
    for tag in ("<script", "<svg", "<style", "[[figure:"):
        print(f"  {tag:<14} x{body.count(tag)}")


def diff(slug, path):
    """Report whether the stored body still matches the file on disk."""
    post = _get(slug)
    with open(path, encoding="utf-8") as fh:
        expected = fh.read()

    if post.content == expected:
        print(f"{slug!r} matches {path} ({len(expected)} chars).")
        return

    print(f"{slug!r} DIFFERS from {path}.")
    print(f"  file:     {len(expected)} chars")
    print(f"  database: {len(post.content)} chars")
    for i, (a, b) in enumerate(zip(expected, post.content)):
        if a != b:
            print(f"  first difference at offset {i}:")
            print(f"    file:     {expected[i : i + 60]!r}")
            print(f"    database: {post.content[i : i + 60]!r}")
            break
    sys.exit(1)


def publish(slug, title, path):
    with open(path, encoding="utf-8") as fh:
        body = fh.read()

    raw = Post.body_needs_raw_html(body)
    post = Post.objects.filter(slug=slug).first()
    if post is None:
        # Post.save() only derives a slug when the field is empty, so the one
        # asked for here is kept as-is.
        post = Post(title=title, content=body, owner=_owner(), slug=slug, raw_html=raw)
        post.save()
        print(f"Created {slug!r} ({len(body)} chars).")
    else:
        # update() skips save() entirely, so date_added is left alone too.
        Post.objects.filter(pk=post.pk).update(title=title, content=body, raw_html=raw)
        print(f"Updated {slug!r} ({len(body)} chars).")

    editor = "plain source textarea" if raw else "rich-text editor"
    print(f"  raw_html={raw} — the admin will show a {editor}.")
    print(f"  /blog/{slug}/")


def main():
    args = sys.argv[1:]
    if len(args) == 2 and args[0] == "--show":
        show(args[1])
    elif len(args) == 3 and args[0] == "--diff":
        diff(args[1], args[2])
    elif len(args) == 3:
        publish(args[0], args[1], args[2])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()

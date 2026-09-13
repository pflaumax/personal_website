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
tracked in git but its images are not, so keep editing the file and re-running
this script. `--diff` reports whether the database still agrees with it, and
tells cosmetic differences (the editor's line endings and entities) apart from a
real change to the prose, the figure tokens, the classes or the block tags.
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

from website_app.figures import fingerprint  # noqa: E402
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


def _first_word_difference(a, b):
    """Where two normalised prose strings part company, in words."""
    left, right = a.split(), b.split()
    for i, (x, y) in enumerate(zip(left, right)):
        if x != y:
            return i, " ".join(left[i : i + 12]), " ".join(right[i : i + 12])
    i = min(len(left), len(right))
    return i, " ".join(left[i : i + 12]), " ".join(right[i : i + 12])


def diff(slug, path):
    """Report whether the stored body still means what the source file says.

    Byte equality is the wrong question after an admin Save. TinyMCE rewrites
    line endings to CRLF, re-encodes non-ASCII punctuation as named entities and
    collapses blank lines — none of which changes a rendered page. Comparing
    bytes made this cry DIFFERS every time, which is useless in exactly the
    situation it exists for.

    So: exact match, else compare fingerprints (see website_app/figures.py) and
    say which it is. Exit status is non-zero only for a real change.
    """
    post = _get(slug)
    with open(path, encoding="utf-8") as fh:
        expected = fh.read()

    if post.content == expected:
        print(f"{slug!r} matches {path} exactly ({len(expected):,} chars).")
        return

    want, got = fingerprint(expected), fingerprint(post.content)
    print(f"{slug!r} is not byte-identical to {path}.")
    print(f"  file {len(expected):,} chars, database {len(post.content):,} chars")

    cosmetic = []
    if post.content.count("\r") != expected.count("\r"):
        cosmetic.append("line endings (CRLF)")
    if post.content.count("&") != expected.count("&"):
        cosmetic.append("character entities")
    if post.content.count("\n") != expected.count("\n"):
        cosmetic.append("blank lines")
    if cosmetic:
        print(f"  cosmetic: {', '.join(cosmetic)}")

    if want == got:
        print(
            f"  structure intact: prose, {len(want['figures'])} figure tokens, "
            f"{len(want['classes'])} class attributes and every block tag agree."
        )
        print("  Nothing to do — the rendered page is unchanged.")
        return

    print("\n  STRUCTURE CHANGED:")
    if want["prose"] != got["prose"]:
        i, a, b = _first_word_difference(want["prose"], got["prose"])
        print(f"    prose differs from word {i}:")
        print(f"      file:     …{a}…")
        print(f"      database: …{b}…")
    if want["figures"] != got["figures"]:
        print(f"    figure tokens: file {want['figures']}")
        print(f"                   database {got['figures']}")
    if want["classes"] != got["classes"]:
        lost = sorted(set(want["classes"]) - set(got["classes"]))
        gained = sorted(set(got["classes"]) - set(want["classes"]))
        if lost:
            print(f"    classes lost: {lost}")
        if gained:
            print(f"    classes added: {gained}")
        if not lost and not gained:
            print("    class attributes reordered or repeated differently")
    for tag, n in want["tags"].items():
        if got["tags"][tag] != n:
            print(f"    <{tag}>: {n} in the file, {got['tags'][tag]} in the database")

    print(f"\n  Re-publish from the file:  python {sys.argv[0]} {slug} <title> {path}")
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

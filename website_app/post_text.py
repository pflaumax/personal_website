"""Turn a post body into plain text — the one pipeline behind every text view.

Three places need the prose out of a body and nothing else: `Post.excerpt` (and
through it the RSS summary and the meta description), and the structural
fingerprint `publish_post.py --diff` compares. They used to do it separately and
each carried the same two bugs.

The order of operations is the whole content of this module, and every step is
here because something went wrong without it:

1. Comments go first. `_NON_PROSE` below pairs an opening style or script tag
   with a closing one by regex, so a body whose comment *named* one of those
   tags let that fake opening tag pair with the real closing tag further down.
   The comment then lost its `-->`, and the tag stripper swallowed everything to
   the next one — which ate the lede out of the excerpt, the RSS summary and the
   meta description of a live post.

2. Style and script blocks next. `strip_tags` drops the tags and keeps what sits
   between them, so a post carrying an inline stylesheet would otherwise open
   its excerpt with raw CSS.

3. Figure tokens after that. `[[figure:name]]` is plain text, so nothing else
   here would touch it, and the literal token turned up in the meta description.

4. Remaining tags are removed, but a *block* boundary first becomes a space.
   `strip_tags` glues the text of adjacent elements together, so
   `<p>one</p><p>two</p>` reads as `onetwo` and a table header row comes out as
   `deliverytotal sizerequests` — whether markup has newlines between its tags
   is the editor's business, not the reader's. Doing this for every tag instead
   is worse in the other direction: `<strong>markup</strong>.` would gain a
   space before the full stop. A block boundary is a word boundary; an inline
   tag is not.

5. Entities are unescaped once, because `strip_tags` leaves them. Otherwise a
   stored `&nbsp;` survives as literal text and whatever renders it escapes the
   ampersand again, so readers see `&amp;nbsp;`.
"""

import html
import re

# Matched as a pair, which is why step 1 above has to happen first.
_NON_PROSE = re.compile(r"<(style|script)\b[^>]*>.*?</\1\s*>", re.I | re.S)

_COMMENT = re.compile(r"<!--.*?-->", re.S)

# Elements that end a run of text. Everything else is inline and is deleted
# without leaving a gap.
_BLOCK_TAG = re.compile(
    r"</?(?:address|article|aside|blockquote|br|dd|div|dl|dt|figcaption|figure"
    r"|footer|h[1-6]|header|hr|li|main|nav|ol|p|pre|section|table|tbody|td"
    r"|tfoot|th|thead|tr|ul)\b[^>]*>",
    re.I,
)

_TAG = re.compile(r"<[^>]*>")


def plain_text(body, strip_tokens=None):
    """The readable text of a post body, whitespace collapsed.

    `strip_tokens` is `website_app.figures.strip_figures`, passed in rather than
    imported so that figures.py can call this without the two importing each
    other.
    """
    text = _COMMENT.sub(" ", body or "")
    text = _NON_PROSE.sub(" ", text)
    if strip_tokens is not None:
        text = strip_tokens(text)
    text = _BLOCK_TAG.sub(" ", text)
    text = _TAG.sub("", text)
    return " ".join(html.unescape(text).split())

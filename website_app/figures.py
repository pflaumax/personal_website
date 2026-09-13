"""Figure tokens: `[[figure:name]]` in a post body, a template partial on disk.

Why a token instead of markup in the body: a figure is code. It carries its own
CSS, sometimes an SVG, occasionally a script — none of which TinyMCE's default
allowlist has elements for, so a body containing one cannot be opened in the
admin without being rewritten (see `Post.raw_html`). A token is plain text. The
editor cannot break it, the prose around it stays editable in the rich-text
editor, and the figure itself lives in
`website_app/templates/website_app/figures/` where it is versioned in git and
can consume the site's own theme tokens as inline markup.

    <p>Its ASCII advance widths are thirteen distinct values.</p>
    [[figure:ms-ui-gothic-widths]]

The logic sits here rather than in the template tag so that `Post.excerpt` can
strip tokens without a model importing a templatetags module — the same split
media_urls.py uses. `templatetags/figures.py` is the thin filter wrapper.
"""

import logging
import re

from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

# Lowercase, digits and hyphens only. This is also the path guard: no dots and
# no slashes can reach the template loader, so a body cannot address anything
# outside the figures directory.
FIGURE_TOKEN = re.compile(r"\[\[figure:([a-z0-9-]+)\]\]")

FIGURE_TEMPLATE = "website_app/figures/{name}.html"


def expand_figures(content):
    """Replace every figure token in `content` with its rendered partial.

    A token naming a figure that does not exist is left in place and logged.
    Failing visibly on one paragraph beats a 500 on the whole post, and an
    unexpanded `[[figure:typo]]` is impossible to miss on the page.
    """
    if not content:
        return ""

    def expand(match):
        name = match.group(1)
        try:
            return render_to_string(FIGURE_TEMPLATE.format(name=name))
        except TemplateDoesNotExist:
            logger.warning("Unknown figure %r left unexpanded in a post body", name)
            return match.group(0)

    return FIGURE_TOKEN.sub(expand, content)


def strip_figures(content):
    """Drop figure tokens, for the plain-text views of a body.

    A token is text, so `strip_tags` leaves it alone — without this the literal
    `[[figure:name]]` turns up in the RSS summary and the meta description.
    Replaced with a space so the words either side do not run together.
    """
    return FIGURE_TOKEN.sub(" ", content or "")

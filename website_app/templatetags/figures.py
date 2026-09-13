"""The `figures` filter: post.html's replacement for `|safe`.

All the logic lives in website_app/figures.py; this is the template-layer
wrapper. See that module for why figures are tokens rather than markup.
"""

from django import template
from django.utils.safestring import mark_safe

from ..figures import expand_figures

register = template.Library()


@register.filter
def figures(content):
    """Render a post body, expanding `[[figure:name]]` tokens.

    Returns a safe string: `Post.content` is author-written HTML that has always
    been served verbatim (this filter replaced `|safe` in post.html), and the
    partials are template files under our own control. Nothing here is user
    input in the untrusted sense — the only writer is the site's own admin.
    """
    return mark_safe(expand_figures(content))  # noqa: S308

from urllib.parse import quote, urlencode

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_exempt

from website_project.decorators import staff_member_required_or_404

from .models import MediaFile, Post
from .projects_data import PROJECTS


@staff_member_required_or_404
def media_list(request):
    """Return a JSON list of media files for TinyMCE"""
    file_type = request.GET.get("type", "image")
    media_files = MediaFile.objects.filter(file_type=file_type).order_by("-uploaded_at")

    media_list = [
        {"title": media.title, "value": media.file_url} for media in media_files
    ]
    return JsonResponse(media_list, safe=False)


# Per-page title and description travel in the context rather than in template
# blocks: a Django block can only be emitted once, and the same title is needed
# in <title>, og:title and twitter:title.
def index(request):
    """Website home page."""
    context = {
        # The three most recent projects, sliced from the same tuple /projects/
        # renders — so the two pages can never drift apart.
        "latest_projects": PROJECTS[:3],
        "page_description": (
            "Max Pflaum — software developer building web applications, "
            "automation tools and scripts in Python. Embedded enthusiast, "
            "Linux and open source."
        ),
    }
    return render(request, "website_app/home.html", context)


def blog(request):
    """Show blog page."""
    blog = Post.objects.all().order_by("-date_added")
    context = {
        "blog": blog,
        "page_title": "Posts",
        "page_description": (
            "Posts by Max Pflaum on software development, tooling and hardware."
        ),
    }
    return render(request, "website_app/blog.html", context)


def post(request, slug):
    """Show post page."""
    post = get_object_or_404(Post, slug=slug)
    context = {
        "post": post,
        "page_title": post.title,
        "page_description": post.meta_description,
        "page_type": "article",
        **_share_links(request, post),
    }
    return render(request, "website_app/post.html", context)


def _share_links(request, post):
    """Build the share targets shown under a post.

    Two destinations only, both open: Bluesky and a mail client. quote_via=quote
    rather than urlencode's default quote_plus, because a mailto body is pasted
    into the message verbatim — `+` for a space is a query-string convention
    that mail clients do not undo, so the reader would see the plus signs.
    """
    url = request.build_absolute_uri(post.get_absolute_url())
    body = f"{post.title}\n\n{url}"
    return {
        # The bare URL, for the copy-link button. Everything else about that
        # button is progressive enhancement, but the address it copies is not
        # something JavaScript should have to reconstruct.
        "share_url": url,
        "share_bluesky_url": "https://bsky.app/intent/compose?"
        + urlencode({"text": body}, quote_via=quote),
        "share_email_url": "mailto:?"
        + urlencode({"subject": post.title, "body": body}, quote_via=quote),
    }


def projects(request):
    """Show projects page."""
    context = {
        "projects": PROJECTS,
        "page_title": "Projects",
        "page_description": (
            "Public projects by Max Pflaum — Django, FastAPI, Celery, ESP32 "
            "and more, with source on GitHub."
        ),
    }
    return render(request, "website_app/projects.html", context)


def contact(request):
    """Show contact page."""
    context = {
        "page_title": "Contact",
        "page_description": (
            "Get in touch with Max Pflaum — email, LinkedIn and GitHub."
        ),
    }
    return render(request, "website_app/contact.html", context)


@csrf_exempt
def healthcheck(request):
    """Ping page"""
    return JsonResponse({"status": "OK"})


def _error_view(status_code, title, body_template, page_title):
    """
    Build a handler400/403/404/500-compatible view rendering the shared
    errors/_base.html. body_template may contain a {contact_url} placeholder,
    filled in at request time — reverse() isn't safe to call at import time,
    before urls.py has finished loading.
    """

    def view(request, exception=None):
        body = body_template.format(contact_url=reverse("website_app:contact"))
        context = {
            "title": title,
            "body": mark_safe(body),
            "page_title": page_title,
            "page_description": title,
            "page_noindex": True,
        }
        return render(
            request, "website_app/errors/_base.html", context, status=status_code
        )

    return view


error_400 = _error_view(
    400,
    "Welcome to 400 | Bad Request",
    "Sorry, your request could not be processed. If this problem persists, "
    'please <a href="{contact_url}">contact me</a>.',
    page_title="400 Bad request",
)
error_403 = _error_view(
    403,
    "Welcome to 403 | Permission Denied",
    "Sorry, you don't have permission to access this page.",
    page_title="403 Permission denied",
)
error_404 = _error_view(
    404,
    "Welcome to 404 | Page not found",
    "If you'd like to flag this broken link, please "
    '<a href="{contact_url}">contact me</a>.',
    page_title="404 Page not found",
)
error_500 = _error_view(
    500,
    "Welcome to 500 | Server error",
    "Something went wrong. If this problem persists, please "
    '<a href="{contact_url}">contact me</a>.',
    page_title="500 Server error",
)


def fadmin(request):
    """Decoy for the real admin path — reuses the 404 page verbatim."""
    return error_404(request)

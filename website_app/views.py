from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_exempt
from website_project.decorators import staff_member_required_or_404

from .models import MediaFile, Post


@staff_member_required_or_404
def media_list(request):
    """Return a JSON list of media files for TinyMCE"""
    file_type = request.GET.get("type", "image")
    media_files = MediaFile.objects.filter(file_type=file_type).order_by("-uploaded_at")

    media_list = [
        {"title": media.title, "value": media.file_url} for media in media_files
    ]
    return JsonResponse(media_list, safe=False)


def index(request):
    """Website home page."""
    return render(request, "website_app/home.html")


def blog(request):
    """Show blog page."""
    blog = Post.objects.all().order_by("-date_added")
    context = {"blog": blog}
    return render(request, "website_app/blog.html", context)


def post(request, slug):
    """Show post page."""
    post = get_object_or_404(Post, slug=slug)
    context = {"post": post}
    return render(request, "website_app/post.html", context)


def projects(request):
    """Show projects page."""
    return render(request, "website_app/projects.html")


def contact(request):
    """Show contact page."""
    return render(request, "website_app/contact.html")


@csrf_exempt
def healthcheck(request):
    """Ping page"""
    return JsonResponse({"status": "OK"})


def _error_view(status_code, title, body_template):
    """
    Build a handler400/403/404/500-compatible view rendering the shared
    errors/_base.html. body_template may contain a {contact_url} placeholder,
    filled in at request time — reverse() isn't safe to call at import time,
    before urls.py has finished loading.
    """

    def view(request, exception=None):
        body = body_template.format(contact_url=reverse("website_app:contact"))
        context = {"title": title, "body": mark_safe(body)}
        return render(
            request, "website_app/errors/_base.html", context, status=status_code
        )

    return view


error_400 = _error_view(
    400,
    "Welcome to 400 | Bad Request",
    "Sorry, your request could not be processed. If this problem persists, "
    'please <a href="{contact_url}">contact me</a>.',
)
error_403 = _error_view(
    403,
    "Welcome to 403 | Permission Denied",
    "Sorry, you don't have permission to access this page.",
)
error_404 = _error_view(
    404,
    "Welcome to 404 | Page not found",
    "If you'd like to flag this broken link, please "
    '<a href="{contact_url}">contact me</a>.',
)
error_500 = _error_view(
    500,
    "Welcome to 500 | Server error",
    "Something went wrong. If this problem persists, please "
    '<a href="{contact_url}">contact me</a>.',
)


def fadmin(request):
    """Decoy for the real admin path — reuses the 404 page verbatim."""
    return error_404(request)

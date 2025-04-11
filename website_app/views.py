from django.shortcuts import render, get_object_or_404
from .models import MediaFile, Post
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required


@staff_member_required
def media_list(request):
    """Return a JSON list of media files for TinyMCE"""
    file_type = request.GET.get("type", "image")
    media_files = MediaFile.objects.filter(file_type=file_type).order_by("-uploaded_at")

    media_list = [
        {"title": media.title, "value": media.file_url} for media in media_files
    ]
    return JsonResponse(media_list, safe=False)


def index(request):
    """Website home page. Pressing on logo name."""
    return render(request, "website_app/home.html")


def home(request):
    """Website home page. Pressing 'Home' button."""
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


def error_404(request, exception):
    context = {}
    return render(request, "website_app/errors/404.html", context, status=404)


def error_500(request):
    context = {}
    return render(request, "website_app/errors/500.html", context, status=500)


def error_403(request, exception):
    context = {}
    return render(request, "website_app/errors/403.html", context, status=403)


def error_400(request, exception):
    context = {}
    return render(request, "website_app/errors/400.html", context, status=400)

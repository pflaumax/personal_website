from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "website_app"
urlpatterns = [
    # Show home page by default.
    path("", views.index, name="index"),
    # Legacy URL, kept as a redirect for existing links/bookmarks.
    path(
        "home/",
        RedirectView.as_view(pattern_name="website_app:index", permanent=True),
        name="home",
    ),
    # Show all posts.
    path("blog/", views.blog, name="blog"),
    # Show post content.
    path("blog/<slug:slug>/", views.post, name="post"),
    # Show projects page.
    path("projects/", views.projects, name="projects"),
    # Show contact page.
    path("contact/", views.contact, name="contact"),
    # Show list of images added.
    path("media-list/", views.media_list, name="media_list"),
    # Ping page
    path("healthcheck/", views.healthcheck, name="healthcheck"),
]

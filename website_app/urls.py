from django.urls import path
from django.views.generic import RedirectView

from . import views
from .feeds import LatestPostsFeed

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
    # RSS. Excluded from page-view stats in stats/middleware.py — every reader
    # poll would otherwise inflate the counters.
    path("feed/", LatestPostsFeed(), name="feed"),
    # Ping page
    path("healthcheck/", views.healthcheck, name="healthcheck"),
]

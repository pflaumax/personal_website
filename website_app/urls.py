from django.urls import path
from . import views

app_name = "website_app"
urlpatterns = [
    # Show home page by default.
    path("", views.index, name="index"),
    # Show home page with 'Home' button.
    path("home/", views.home, name="home"),
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
]

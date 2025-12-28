from django.urls import path
from . import views


app_name = "tools"

urlpatterns = [
    # Tools page
    path("", views.tools_view, name="tools"),
]

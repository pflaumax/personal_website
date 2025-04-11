from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path("admin/", admin.site.urls),
    path("tools/", include("tools.urls")),
    path("", include("website_app.urls")),
    path("tinymce/", include("tinymce.urls")),
]


handler404 = "website_app.views.error_404"
handler500 = "website_app.views.error_500"
handler403 = "website_app.views.error_403"
handler400 = "website_app.views.error_400"


# Always serve media files regardless of DEBUG setting
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

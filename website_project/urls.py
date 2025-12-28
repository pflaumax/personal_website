from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from website_app.views import fadmin
import debug_toolbar


urlpatterns = [
    path("tools/", include("tools.urls")),
    path("", include("website_app.urls")),
    path("tinymce/", include("tinymce.urls")),
    path(f"{settings.ADMIN_URL}/", admin.site.urls),
    path("admin/", fadmin),
    path("api/stats/", include("stats.urls")),
]

handler404 = "website_app.views.error_404"
handler500 = "website_app.views.error_500"
handler403 = "website_app.views.error_403"
handler400 = "website_app.views.error_400"


# Always serve media files regardless of DEBUG setting
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Only include debug toolbar if DEBUG is True
if settings.DEBUG:
    urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]

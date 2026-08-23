from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from website_app.views import fadmin

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


# Development only: static() returns [] when DEBUG is False. In production
# media is served by Nginx straight from MEDIA_ROOT — the request never
# reaches Django.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# django-debug-toolbar is a dev-only dependency (requirements-dev.txt) and
# is not installed in production — the import must stay inside this guard.
if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]

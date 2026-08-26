from functools import lru_cache

from django.conf import settings
from django.db.models import F

from .models import PageView

# Keep in sync with PageView.path's max_length.
MAX_TRACKED_PATH_LENGTH = 512

EXCLUDED_PATHS = {
    "/favicon.ico",
    "/healthcheck/",
    "/robots.txt",
    # JSON endpoint backing the TinyMCE media picker — an API call made from
    # the admin, not a page view.
    "/media-list/",
    # RSS. A reader polls this on a schedule forever; counting it would drown
    # the real page views.
    "/feed/",
}

EXCLUDED_SUFFIXES = {
    ".js",
    ".css",
    ".png",
    ".jpg",
    ".jpeg",
    ".svg",
    ".webp",
    ".ico",
}


@lru_cache(maxsize=1)
def _excluded_prefixes():
    """
    Path prefixes that are never page views. Cached because the result cannot
    change during the process lifetime; tests that patch ADMIN_URL must call
    _excluded_prefixes.cache_clear().
    """
    prefixes = {
        "/static/",
        "/media/",
        "/admin/",
        "/api/",
        # django-tinymce mounts flatpages_link_list/, compressor/ and
        # filebrowser/ here, unconditionally in production. They are editor
        # API calls made from the admin, not page views.
        "/tinymce/",
    }

    # The real admin lives at settings.ADMIN_URL, not the /admin/ decoy above —
    # without this, admin traffic (including login attempts) is tracked and
    # exposed via the stats API. The trailing slash matters: a bare "/panel"
    # prefix would also swallow public pages like "/panel-discussion/".
    admin_url = settings.ADMIN_URL.strip().strip("/").strip()
    if admin_url:
        prefixes.add(f"/{admin_url}/")

    return prefixes


class PageViewMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        response = self.get_response(request)

        if self._is_trackable(request, path, response):
            self._record_page_view(path)

        return response

    def _is_trackable(self, request, path, response):
        if request.method != "GET":
            return False
        # Only successful renders count. Redirects are explicitly excluded:
        # a 301 means the page was never rendered, and counting it would
        # double-count every visit (once for the redirect, once for its
        # target) and keep retired URLs alive in the stats forever.
        if not 200 <= response.status_code < 300:
            return False
        if path in EXCLUDED_PATHS:
            return False
        if any(path.startswith(prefix) for prefix in _excluded_prefixes()):
            return False
        if any(path.endswith(suffix) for suffix in EXCLUDED_SUFFIXES):
            return False
        # Skip rather than truncate: path is unique, so two distinct URLs
        # sharing their first MAX_TRACKED_PATH_LENGTH characters would collapse
        # into one row and misattribute each other's views. Paths this long
        # essentially only come from scanners, which no longer reach 2xx.
        if len(path) > MAX_TRACKED_PATH_LENGTH:
            return False
        return True

    def _record_page_view(self, path):
        # Atomic increment — avoids the lost-update race of the old
        # get_or_create() -> obj.count += 1 -> obj.save() sequence, where
        # two concurrent requests could read the same count and overwrite
        # each other's write.
        updated = PageView.objects.filter(path=path).update(count=F("count") + 1)
        if updated:
            return

        _, created = PageView.objects.get_or_create(path=path, defaults={"count": 1})
        if not created:
            # Lost the race: another request created the row between our
            # update() above and this get_or_create().
            PageView.objects.filter(path=path).update(count=F("count") + 1)

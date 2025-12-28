from .models import PageView


class PageViewMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # Define exclusion patterns
        excluded_paths = {
            "/favicon.ico",
            "/healthcheck/",
            "/robots.txt",
        }

        excluded_prefixes = {
            "/static/",
            "/admin/",
            "/api/",
        }

        excluded_suffixes = {
            ".js",
            ".css",
            ".png",
            ".jpg",
            ".jpeg",
            ".svg",
            ".webp",
            ".ico",
        }

        # Check if current path matches any excluded path exactly
        if path in excluded_paths:
            return self.get_response(request)

        # Check if path starts with any excluded prefix
        for prefix in excluded_prefixes:
            if path.startswith(prefix):
                return self.get_response(request)

        # Check if path ends with any excluded suffix
        for suffix in excluded_suffixes:
            if path.endswith(suffix):
                return self.get_response(request)

        # If we get here, the path is not excluded
        if request.method == "GET":
            obj, _ = PageView.objects.get_or_create(path=path)
            obj.count += 1
            obj.save()

        return self.get_response(request)

from django.http import JsonResponse
from .models import PageView


def stats_view(request):
    # Get limit from query parameter, default to 10
    limit = request.GET.get("limit", 10)
    try:
        limit = int(limit)
    except ValueError:
        limit = 10

    views = PageView.objects.all().order_by("-count")
    all_views = views  # Keep a reference to all views for summary stats

    # Apply limit for the pages list
    views = views[:limit]

    data = {
        "summary": {
            "total_page_views": sum(v.count for v in all_views),
            "unique_pages": all_views.count(),
        },
        "pages": [{"path": view.path, "count": view.count} for view in views],
    }

    return JsonResponse(data)

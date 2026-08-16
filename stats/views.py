from django.db.models import Count, Sum
from django.http import JsonResponse

from website_project.decorators import staff_member_required_or_404

from .models import PageView

DEFAULT_LIMIT = 10
MAX_LIMIT = 100


@staff_member_required_or_404
def stats_view(request):

    try:
        limit = int(request.GET.get("limit", DEFAULT_LIMIT))
    except (TypeError, ValueError):
        limit = DEFAULT_LIMIT
    limit = max(0, min(limit, MAX_LIMIT))

    views = PageView.objects.order_by("-count", "path")
    summary = views.aggregate(total_page_views=Sum("count"), unique_pages=Count("id"))

    data = {
        "summary": {
            "total_page_views": summary["total_page_views"] or 0,
            "unique_pages": summary["unique_pages"] or 0,
        },
        "pages": [{"path": view.path, "count": view.count} for view in views[:limit]],
    }

    return JsonResponse(data)

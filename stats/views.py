from django.shortcuts import render
from django.http import JsonResponse
from .models import PageView


def stats_view(request):
    # Check if wants only specific data
    format_type = request.GET.get("format", "full")

    # For ESP, only root views
    if format_type == "simple":
        try:
            root_view = PageView.objects.get(path="/")
            return JsonResponse({"/": root_view.count})
        except PageView.DoesNotExist:
            return JsonResponse({"/": 0})

    # Full structured response for web/other clients
    views = PageView.objects.all().order_by("-count")

    data = {
        "summary": {
            "total_page_views": sum(view.count for view in views),
            "unique_pages": len(views),
        },
        "pages": [{"path": view.path, "count": view.count} for view in views],
    }

    return JsonResponse(data)

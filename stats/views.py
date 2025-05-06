from django.shortcuts import render
from django.http import JsonResponse
from .models import PageView


def stats_view(request):
    views = PageView.objects.all().order_by("-count")

    data = {
        "summary": {
            "total_page_views": sum(view.count for view in views),
            "unique_pages": len(views),
        },
        "pages": [{"path": view.path, "count": view.count} for view in views],
    }

    return JsonResponse(data)

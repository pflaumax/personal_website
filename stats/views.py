from django.shortcuts import render
from django.http import JsonResponse
from .models import PageView


def stats_view(request):
    views = PageView.objects.all().order_by("-count")

    # Create a structured response
    structured_data = {
        "summary": {
            "total_page_views": sum(view.count for view in views),
            "unique_pages": len(views),
        },
        "pages": [{"path": view.path, "count": view.count} for view in views],
    }

    # Also include flat format for backward compatibility
    flat_data = {view.path: view.count for view in views}

    # Combine both formats
    combined_data = {
        **flat_data,  # Include flat key-value pairs
        **structured_data,  # Include structured data
    }

    return JsonResponse(combined_data)

from django.shortcuts import render


def tools_view(request):
    """Render the tools page with Todo and Pomodoro apps"""
    context = {
        "page_title": "Tools",
        "page_description": (
            "A browser-based todo list and Pomodoro timer. No account and no "
            "storage — everything stays in the tab."
        ),
    }
    return render(request, "tools/tools.html", context)

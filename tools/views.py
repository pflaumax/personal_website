from django.shortcuts import render


def tools_view(request):
    """Render the tools page with Todo and Pomodoro apps"""
    return render(request, "tools/tools.html")

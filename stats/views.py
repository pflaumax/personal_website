from django.shortcuts import render
from django.http import JsonResponse
from .models import PageView


def stats_view(request):
    views = PageView.objects.all()
    data = {view.path: view.count for view in views}
    return JsonResponse(data)

from django.contrib import admin

from .models import PageView


@admin.register(PageView)
class PageViewAdmin(admin.ModelAdmin):
    """
    Read-only: PageViewMiddleware is the only legitimate writer, so the table
    is a record of what happened. Deletion stays available for pruning junk
    paths, but counts and paths cannot be edited or invented by hand.
    """

    list_display = ("path", "count")
    search_fields = ("path",)
    ordering = ("-count", "path")
    readonly_fields = ("path", "count")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

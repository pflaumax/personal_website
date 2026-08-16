from functools import wraps

from django.http import Http404


def staff_member_required_or_404(view_func):
    """
    Like admin.views.decorators.staff_member_required, but raises Http404 for
    non-staff users instead of redirecting to the admin login page. That
    redirect leaks settings.ADMIN_URL in the Location header.
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not (request.user.is_active and request.user.is_staff):
            raise Http404
        return view_func(request, *args, **kwargs)

    return wrapper

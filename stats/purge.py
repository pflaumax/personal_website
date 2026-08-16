def admin_path_prefix(admin_url):
    """
    Build the path prefix for an admin URL, or None if it is degenerate.

    A blank or "/"-only value would produce the prefix "/", which matches
    every tracked path — deleting the entire table rather than admin rows.
    """
    cleaned = (admin_url or "").strip().strip("/").strip()
    if not cleaned:
        return None
    return f"/{cleaned}/"


def purge_admin_pageviews(page_view_model, admin_url):
    """
    Delete page views recorded under the given admin URL.

    Returns the number of rows deleted, or None if admin_url was degenerate
    and nothing was attempted. Safe to run repeatedly.
    """
    prefix = admin_path_prefix(admin_url)
    if prefix is None:
        return None

    deleted, _ = page_view_model.objects.filter(path__startswith=prefix).delete()
    return deleted

from django.conf import settings
from django.db import migrations

from stats.purge import purge_admin_pageviews


def purge(apps, schema_editor):
    """
    Best-effort historical cleanup of page views recorded under the admin path
    before PageViewMiddleware started excluding it.
    """
    purge_admin_pageviews(apps.get_model("stats", "PageView"), settings.ADMIN_URL)


class Migration(migrations.Migration):

    dependencies = [
        ("stats", "0002_alter_pageview_path"),
    ]

    operations = [
        migrations.RunPython(purge, migrations.RunPython.noop),
    ]

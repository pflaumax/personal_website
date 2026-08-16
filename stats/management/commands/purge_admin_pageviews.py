from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from stats.models import PageView
from stats.purge import admin_path_prefix, purge_admin_pageviews


class Command(BaseCommand):
    help = (
        "Delete page views recorded under an admin path. Defaults to the "
        "current DJANGO_ADMIN_URL; pass --prefix to clean up a rotated one."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--prefix",
            help=(
                "Admin URL to purge instead of the configured one. Use this "
                "after rotating DJANGO_ADMIN_URL to clear the old path's rows."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be deleted without deleting it.",
        )

    def handle(self, *args, **options):
        admin_url = options["prefix"] or settings.ADMIN_URL

        prefix = admin_path_prefix(admin_url)
        if prefix is None:
            raise CommandError(
                f"Refusing to purge: {admin_url!r} resolves to the prefix '/', "
                "which would match every tracked path and delete the whole table."
            )

        if options["dry_run"]:
            count = PageView.objects.filter(path__startswith=prefix).count()
            self.stdout.write(f"Would delete {count} page view(s) under {prefix}")
            return

        deleted = purge_admin_pageviews(PageView, admin_url)
        self.stdout.write(
            self.style.SUCCESS(f"Deleted {deleted} page view(s) under {prefix}")
        )

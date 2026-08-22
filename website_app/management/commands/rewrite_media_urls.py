from django.core.management.base import BaseCommand

from website_app.media_urls import (
    LEGACY_S3_MEDIA_PREFIX,
    LOCAL_MEDIA_PREFIX,
    rewrite_posts,
)
from website_app.models import Post


class Command(BaseCommand):
    help = (
        "Rewrite absolute S3 media URLs in post bodies to site-relative "
        "/media/ paths. Safe to run repeatedly."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--prefix",
            default=LEGACY_S3_MEDIA_PREFIX,
            help="Absolute media prefix to replace (default: the legacy S3 bucket URL).",
        )
        parser.add_argument(
            "--replacement",
            default=LOCAL_MEDIA_PREFIX,
            help=f"What to replace it with (default: {LOCAL_MEDIA_PREFIX}).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without writing anything.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        changed = rewrite_posts(
            Post,
            legacy_prefix=options["prefix"],
            media_prefix=options["replacement"],
            commit=not dry_run,
        )

        if not changed:
            self.stdout.write("No posts reference that prefix — nothing to do.")
            return

        verb = "Would rewrite" if dry_run else "Rewrote"
        total = sum(replacements for _, replacements in changed)
        for slug, replacements in changed:
            self.stdout.write(f"  {slug}: {replacements} URL(s)")

        message = f"{verb} {total} URL(s) across {len(changed)} post(s)"
        self.stdout.write(
            message if dry_run else self.style.SUCCESS(message)
        )

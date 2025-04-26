from django.apps import AppConfig


class WebsiteAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "website_app"

    def ready(self):
        from django.conf import settings
        from storages.backends.s3boto3 import S3Boto3Storage

        if getattr(settings, "USE_S3", False):
            # Force the default storage to be S3Boto3Storage
            import django.core.files.storage

            django.core.files.storage.default_storage = S3Boto3Storage()

from django.apps import AppConfig
from django.core.files.storage import default_storage
import django.db.models.fields.files


class WebsiteAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "website_app"

    def ready(self):
        # Monkey patch the FileField to always use default_storage
        original_init = django.db.models.fields.files.FileField.__init__

        def patched_init(self, *args, **kwargs):
            if "storage" not in kwargs:
                kwargs["storage"] = default_storage
            original_init(self, *args, **kwargs)

        django.db.models.fields.files.FileField.__init__ = patched_init

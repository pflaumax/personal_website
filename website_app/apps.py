import logging

from django.apps import AppConfig
from django.core.files.storage import default_storage

logger = logging.getLogger(__name__)


class WebsiteAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "website_app"

    def ready(self):
        logger.info("Default storage class: %s", default_storage.__class__.__name__)

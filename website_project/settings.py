import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Admin URL
ADMIN_URL = os.getenv("DJANGO_ADMIN_URL")
if not ADMIN_URL:
    raise ValueError("Missing required environment variable: DJANGO_ADMIN_URL")

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("Missing required environment variable: SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DEBUG", "False") == "True"

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")


CSRF_TRUSTED_ORIGINS = [
    origin for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if origin
]

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_HSTS_SECONDS = 3600

# Media lives on local disk and is served by Nginx (see deployment/). The site
# used to switch to S3 on a USE_S3 env flag; that bucket was deleted in August
# 2026 and the files were moved here, so the flag, the AWS_* settings and the
# boto3/django-storages dependencies are gone. Post bodies that still held
# absolute bucket URLs were rewritten by `manage.py rewrite_media_urls`.
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# DEFAULT_FILE_STORAGE and STATICFILES_STORAGE were removed in Django 5.1;
# STORAGES is the current API.
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Application definition

INSTALLED_APPS = [
    # My apps
    "website_app",
    "tools",
    "stats",
    # Third party apps
    "tinymce",
    # Default apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "stats.middleware.PageViewMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

if DEBUG:
    INSTALLED_APPS += ["django_extensions", "debug_toolbar"]
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")

ROOT_URLCONF = "website_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "website_app/templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "website_project.wsgi.application"

# Database configuration
if os.environ.get("DATABASE_URL"):
    # Use PostgreSQL in production
    # ssl_require=False for local Pi connections; set to True for remote/cloud DBs
    _db_url = os.environ.get("DATABASE_URL", "")
    _ssl_require = "localhost" not in _db_url and "127.0.0.1" not in _db_url
    DATABASES = {
        "default": dj_database_url.config(
            default=_db_url,
            conn_max_age=600,
            ssl_require=_ssl_require,
        )
    }
else:
    # Use SQLite locally
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = "/static/"
STATICFILES_DIRS = [os.path.join(BASE_DIR, "website_app/static")]
STATIC_ROOT = BASE_DIR / "staticfiles"


# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Logging
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s %(levelname)s %(name)s: %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
}

# TinyMCE configuration
TINYMCE_DEFAULT_CONFIG = {
    "height": 360,
    "width": "100%",
    "cleanup_on_startup": True,
    "custom_undo_redo_levels": 20,
    "selector": "textarea",
    "theme": "silver",
    "plugins": """
        save link image media preview codesample
        table code lists fullscreen insertdatetime nonbreaking
        directionality searchreplace wordcount visualblocks
        visualchars autolink charmap
        anchor pagebreak
        """,
    "toolbar1": """
        fullscreen preview bold italic underline | fontselect
        fontsizeselect | forecolor backcolor | alignleft alignright |
        aligncenter alignjustify | indent outdent | bullist numlist table |
        link image media | codesample
        """,
    "contextmenu": "formats | link image media",
    "menubar": True,
    "statusbar": True,
    "remove_script_host": False,
    "relative_urls": False,
    "image_list": "/media-list/?type=image",
    "media_list": "/media-list/?type=audio",
}

INTERNAL_IPS = [
    "127.0.0.1",
]

SHELL_PLUS = "ipython"

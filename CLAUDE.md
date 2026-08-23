# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

All commands assume the venv is active: `source .venv/bin/activate` (Python 3.14 locally; README targets 3.12+).

```bash
python manage.py runserver              # dev server
python manage.py migrate
python manage.py makemigrations <app>
python manage.py collectstatic          # required before prod; WhiteNoise uses a manifest
python manage.py shell_plus             # django-extensions (SHELL_PLUS=ipython, not installed by default)

python manage.py test                   # whole suite
python manage.py test website_app       # one app
python manage.py test stats.tests.SomeTestCase.test_method   # one test

python scripts/create_superuser.py      # idempotent, reads DJANGO_SUPERUSER_* from .env
```

There is no lint/format/type-check config in the repo (no pyproject/setup.cfg/ruff/mypy.ini) and no test framework beyond Django's runner. Tests use `django.test.TestCase` and live in `website_app/tests.py`, `stats/tests.py`, and `tools/tests.py`. Coverage is concentrated on `Post.save()` slug generation, `PageViewMiddleware` exclusion rules, and `/api/stats/` authorization — the areas most likely to break silently.

**Every `manage.py` command needs a populated `.env`.** `website_project/settings.py` raises `ValueError` at import if `DJANGO_ADMIN_URL` or `SECRET_KEY` is missing, so a missing `.env` breaks even `--help`.

## Architecture

Django 5.2 project, `website_project/` is the config package; three first-party apps.

**`website_app`** — blog, static pages, media, error handlers. Owns `base.html` (site nav, footer) which every other template in the project extends, and the only CSS/JS bundle (`static/website_app/`). `Post.save()` auto-generates a unique slug from the title, re-slugging only when the title actually changes (`title_has_changed()` re-fetches the row to compare); collisions get a `-1`, `-2` suffix. Views are plain function views; the four `error_4xx/500` views are wired as `handler400/403/404/500` in `website_project/urls.py`.

**`tools`** — a single template-rendering view. Its Todo List and Pomodoro Timer are entirely client-side (`static/website_app/js/tools.js`, browser session storage). The app has **no `models.py`**; migrations `0001`–`0003` create and then delete a `Task` model — that history is intentional, do not "fix" it by adding models back.

**`stats`** — `PageViewMiddleware` increments a per-path `PageView` counter, atomically via `F("count") + 1`. It records **after** the response, and only for `GET` requests that returned 2xx — redirects, 404s and errors are not counted, so bot scans no longer create rows. Exclusions in `stats/middleware.py`: exact paths (incl. `/media-list/`), asset suffixes, over-length paths, and the prefixes `/static/ /media/ /admin/ /api/ /tinymce/` plus `settings.ADMIN_URL` (the `/admin/` entry is only the decoy route). Any new non-page endpoint must be added there.

`/api/stats/` is **staff-only** — it returns 404 for everyone else via `staff_member_required_or_404` (`website_project/decorators.py`), which raises `Http404` instead of redirecting, because Django's own `staff_member_required` leaks `ADMIN_URL` in the `Location` header. `?limit=` is clamped to `[0, 100]`; `0` means summary-only. Purge admin rows recorded before these fixes with `python manage.py purge_admin_pageviews [--prefix <old-url>] [--dry-run]`.

### Storage: local disk only

`settings.py` defines a single `STORAGES` dict (Django 5.1+ API): `STORAGES["default"]` is always `FileSystemStorage` (`MEDIA_ROOT = BASE_DIR/media`, `MEDIA_URL = /media/`); `STORAGES["staticfiles"]` is WhiteNoise's `CompressedManifestStaticFilesStorage` (content-hashed filenames, gzip precompression — `collectstatic` must run before every deploy).

**There is no S3 any more.** The site used to switch backends on a `USE_S3` env flag; that bucket was deleted in August 2026, the 26 files were restored to local disk, and the flag, the `AWS_*` settings, `boto3` and `django-storages` were all removed. Post bodies holding absolute bucket URLs were rewritten by `python manage.py rewrite_media_urls` (idempotent, `--dry-run` available; `website_app/media_urls.py` keeps the legacy prefix as a deliberate hardcoded literal). Migrations `website_app/0005`/`0006` were rewritten so migration history no longer imports the S3 backend — `storage` is not a database-level attribute, so the schema is unchanged. Do not re-add a per-field storage argument: `STORAGES["default"]` is the only mechanism.

`media/` is **tracked in git** — those files are already served publicly, so tracking them leaks nothing, and it is their offsite backup now that S3 is gone. A fresh clone (and every deploy, which is a `git pull`) gets working media. `MediaFile.save()` logs storage diagnostics via `logging` (`website_app.models`), not `print()`.

In production Nginx serves `/media/` and `/static/` straight from disk — the `static(settings.MEDIA_URL, ...)` call in `urls.py` returns `[]` whenever `DEBUG` is False, so it is a dev-only helper. **The public domain reaches the site through Nginx too**: the cloudflared tunnel points at `127.0.0.1:80`, not at Gunicorn. If it is ever pointed back at `:8000`, `/media/` will 404 publicly while still working over LAN, because WhiteNoise serves `STATIC_ROOT` only.

`tools.js`'s alarm sound and any other static asset must be referenced via `{% static %}` (or read from a `data-*` attribute populated by `{% static %}`, see `tools/templates/tools/tools.html`) — a hardcoded `/static/...` path breaks once manifest hashing renames the file.

### Database

`DATABASE_URL` present → Postgres via `dj_database_url`, with `ssl_require` auto-disabled for `localhost`/`127.0.0.1` (the Pi talks to a local Postgres). Absent → SQLite at `db.sqlite3`. `db.sqlite3` and `data.json` are gitignored; `scripts/migrate.py` loads `data.json` if present, skipping the load step otherwise.

### Admin and TinyMCE

The real admin lives at `settings.ADMIN_URL` from the env; `/admin/` is a decoy route mapped to `website_app.views.fadmin`, which renders the 404 page. Post bodies are TinyMCE `HTMLField`s rendered with `|safe`.

To embed media in a post, the file must first exist as a `MediaFile` in admin: `TINYMCE_DEFAULT_CONFIG` points `image_list`/`media_list` at `/media-list/?type=image|audio` (the only two `MediaFile.MEDIA_TYPE_CHOICES`), served by the `media_list` view, gated with `staff_member_required_or_404` (`website_project/decorators.py`) rather than Django's own `staff_member_required` — the latter redirects anonymous users to the admin login page, leaking `settings.ADMIN_URL` via the `Location` header.

`debug_toolbar` and `django_extensions` are dev-only (`requirements-dev.txt`, not installed in prod) — both `INSTALLED_APPS`/`MIDDLEWARE` entries and the `import debug_toolbar` in `urls.py` are gated behind `if DEBUG`. Production always runs `DEBUG=False`.

## Deployment

Self-hosted on a Raspberry Pi 4: Nginx → Gunicorn under a `django-website` systemd unit (`sudo systemctl restart django-website`), Postgres local. Step-by-step guides live in `deployment/` — note that directory and `media_for_blogposts/` are **gitignored and local-only**, so they won't appear on a fresh clone.

`.github/workflows/ping.yml` curls `https://pflaumax.dev/healthcheck/` every 10 minutes; `/healthcheck/` is `@csrf_exempt` (no `@require_GET` — HEAD requests must pass too) and excluded from page-view stats.

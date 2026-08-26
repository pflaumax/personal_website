# Personal Website

A personal website built with Django, featuring a blog with a rich-text CMS, a tools page with productivity apps, and a page view analytics system.

**Live:** [pflaumax.dev](https://pflaumax.dev)


## Features

- **Blog** — Rich-text posts managed via TinyMCE in the Django admin. Posts use auto-generated unique slugs and support embedded images and audio. Each post carries a link back to the list, a share row (Bluesky, email, copy link) and a back-to-top control that only appears when the page is actually long enough to need one.

- **RSS Feed** — `/feed/` via `django.contrib.syndication`, also advertised in `<head>` for reader auto-discovery. Served as `application/xml` rather than `application/rss+xml` so browsers render it instead of downloading a file.

- **Light and Dark Themes** — Three states, not two: with no stored choice the site follows the OS, and an explicit choice is remembered and applied before first paint so the page never flashes the wrong theme. Font weights are tuned per theme — light strokes look heavier on a dark ground, so the dark set steps down to keep the perceived weight equal.

- **Typography** — A single 59 KB variable Monaspace subset (`wght 200..800` plus a `slnt` axis for real obliques). `font-synthesis: none` is set deliberately, so a missing weight shows rather than being faked by the browser.

- **Tools Page** — Client-side productivity apps (Todo List and Pomodoro Timer) built with vanilla JavaScript. Data persists in browser session storage — no backend required. Deliberately not in the primary nav: it is linked from the project that contains it, because it is a demo rather than a product.

- **Page View Analytics** — Custom middleware counts successful (2xx) GET requests per path, excluding static and media files, admin, API and editor routes. Stats are available to staff users in the Django admin, and via a staff-only JSON API at `/api/stats/` — the endpoint returns 404 to everyone else.

- **Media Management** — A `MediaFile` model supports image and audio uploads. Files are stored on local disk under `MEDIA_ROOT` and served by Nginx; they are tracked in git, so a fresh clone has working media.

- **Custom Error Pages** — Styled 400, 403, 404, and 500 error handlers.

- **Healthcheck Endpoint** — `/healthcheck/` returns a JSON `{"status": "OK"}` response, pinged every 10 minutes by a GitHub Actions workflow.


## Tech Stack

| Layer       | Technology                                                    |
|-------------|-----------------------------------------------------------------|
| Backend     | Python 3.12+, Django 5.2, Gunicorn                             |
| Frontend    | HTML, CSS, JavaScript (no framework, no build step, no npm)     |
| Type        | Monaspace Neon (variable subset, self-hosted)                   |
| Lint/Format | Ruff (`pyproject.toml`, dev-only)                               |
| Database    | PostgreSQL (self-hosted on Raspberry Pi, prod), SQLite (dev)  |
| Media       | Local filesystem, served by Nginx                              |
| Rich Text   | TinyMCE (`django-tinymce`)                                     |
| Static Files| WhiteNoise (content-hashed, gzip-precompressed)                |
| CI/CD       | GitHub Actions (healthcheck ping)                               |
| Hosting     | Self-hosted on Raspberry Pi 4 (Nginx, Gunicorn, systemd)       |


## Project Structure

```
personal_website/
├── website_project/      # Django project settings, URLs, WSGI/ASGI
│   └── decorators.py     # Shared staff_member_required_or_404
├── website_app/          # Main app — blog, pages, media, error handlers
│   ├── models.py         # Post and MediaFile models
│   ├── views.py          # Home, blog, projects, contact, healthcheck
│   ├── feeds.py          # RSS feed at /feed/
│   ├── projects_data.py  # The project list — one source for /projects/ and home
│   ├── media_urls.py     # Legacy S3 → local media URL rewriting
│   ├── templates/        # HTML templates (base, pages, error pages)
│   └── static/           # CSS, JS, images, fonts, sounds
├── tools/                # Tools app — Todo List & Pomodoro Timer
├── stats/                # Page view analytics app
│   ├── models.py         # PageView model
│   ├── middleware.py     # Request tracking middleware
│   ├── purge.py          # Shared admin-path purge helper
│   └── views.py          # JSON stats API (staff-only)
├── scripts/              # Utility scripts (migrate, create superuser)
├── deployment/           # Raspberry Pi deployment guides & scripts
├── .github/workflows/    # GitHub Actions (healthcheck ping)
├── requirements.txt      # Production dependencies
├── requirements-dev.txt  # + local dev tooling (debug toolbar, shell_plus, ruff)
├── pyproject.toml        # Ruff configuration
├── manage.py
└── .env.example
```


## Getting Started

### Prerequisites

- Python 3.12+
- pip

### Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd personal_website
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies. For local development with `DEBUG=True` (adds `django-debug-toolbar` and `shell_plus`), use `requirements-dev.txt`:
   ```bash
   pip install -r requirements-dev.txt   # local dev
   # or: pip install -r requirements.txt # production
   ```

4. Configure environment variables — copy the example and fill in your values:
   ```bash
   cp .env.example .env
   ```

   Key variables:
   | Variable                     | Description                          |
   |------------------------------|--------------------------------------|
   | `SECRET_KEY`                 | Django secret key                    |
   | `DEBUG`                      | `True` for development               |
   | `ALLOWED_HOSTS`              | Comma-separated hostnames            |
   | `DJANGO_ADMIN_URL`           | Custom admin URL path (security)     |
   | `DATABASE_URL`               | PostgreSQL connection string (optional — defaults to SQLite) |

5. Run migrations and start the dev server:
   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

6. (Optional) Create a superuser for the admin panel:
   ```bash
   python scripts/create_superuser.py
   ```
   Or set `DJANGO_SUPERUSER_*` variables in `.env` and run the script.


### Editing static files

WhiteNoise's manifest storage is used with `DEBUG=True` as well, so this is not optional in
development: a new or edited file under `static/` returns a 500 (`Missing staticfiles manifest
entry`) until `collectstatic` has run, and `runserver` caches the manifest at startup, so it keeps
serving the old hashed name until it is restarted.

```bash
python manage.py collectstatic   # then restart the server
```


### Tests and linting

```bash
python manage.py test            # whole suite
python manage.py test website_app

ruff check .                     # E, F, I, UP
ruff format .                    # double quotes, line length 88
```

Tests use `django.test.TestCase` and live in each app's `tests.py`. Coverage is concentrated on the
things that break silently rather than loudly: slug generation, the analytics middleware's
exclusion rules, `/api/stats/` authorization, the feed's content type and date handling, and
per-page metadata.


## License

This project is licensed under the [MIT License](LICENSE).

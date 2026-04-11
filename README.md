# Personal Website

A personal website built with Django, featuring a blog with a rich-text CMS, a tools page with productivity apps, and a page view analytics system.

**Live:** [pflaumax.dev](https://pflaumax.dev)


## Features

- **Blog** — Rich-text posts managed via TinyMCE in the Django admin. Posts use auto-generated unique slugs and support embedded images, audio, video, and documents uploaded to AWS S3.

- **Tools Page** — Client-side productivity apps (Todo List and Pomodoro Timer) built with vanilla JavaScript. Data persists in browser session storage — no backend required.

- **Page View Analytics** — Custom middleware tracks GET requests per path (excluding static files, admin, and API routes). Stats are exposed via a JSON API at `/api/stats/`.

- **Media Management** — A `MediaFile` model supports multiple file types (image, audio, video, document). Files are stored on AWS S3 in production or locally in development, controlled by the `USE_S3` environment variable.

- **Custom Error Pages** — Styled 400, 403, 404, and 500 error handlers.

- **Healthcheck Endpoint** — `/healthcheck/` returns a JSON `{"status": "OK"}` response, pinged every 10 minutes by a GitHub Actions workflow to keep the Render instance alive.


## Tech Stack

| Layer       | Technology                                                    |
|-------------|---------------------------------------------------------------|
| Backend     | Python 3.13, Django 5.2, Django REST Framework, Gunicorn      |
| Frontend    | HTML, CSS, JavaScript (no framework)                          |
| Database    | PostgreSQL (self-hosted on Raspberry Pi, prod), SQLite (dev) |
| Media       | AWS S3 via `django-storages` + `boto3`                        |
| Rich Text   | TinyMCE (`django-tinymce`)                                    |
| Static Files| WhiteNoise                                                    |
| CI/CD       | GitHub Actions (healthcheck ping)                             |
| Hosting     | Self-hosted on Raspberry Pi 4 (Nginx, Gunicorn, Supervisor) |


## Project Structure

```
personal_website/
├── website_project/      # Django project settings, URLs, WSGI/ASGI
├── website_app/          # Main app — blog, pages, media, error handlers
│   ├── models.py         # Post and MediaFile models (S3-aware)
│   ├── views.py          # Home, blog, projects, contact, healthcheck
│   ├── templates/        # HTML templates (base, pages, error pages)
│   ├── static/           # CSS, JS, images, fonts, sounds
│   └── middleware.py     # Storage debug middleware
├── tools/                # Tools app — Todo List & Pomodoro Timer
├── stats/                # Page view analytics app
│   ├── models.py         # PageView model
│   ├── middleware.py      # Request tracking middleware
│   └── views.py          # JSON stats API
├── scripts/              # Utility scripts (migrate, create superuser)
├── deployment/           # Raspberry Pi deployment guides & scripts
├── .github/workflows/    # GitHub Actions (healthcheck ping)
├── requirements.txt
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

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
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
   | `USE_S3`                     | `True` to enable AWS S3 media storage |
   | `AWS_ACCESS_KEY_ID`          | AWS credentials (if `USE_S3=True`)   |
   | `AWS_SECRET_ACCESS_KEY`      | AWS credentials (if `USE_S3=True`)   |
   | `AWS_STORAGE_BUCKET_NAME`    | S3 bucket name                       |
   | `AWS_S3_REGION_NAME`         | S3 region                            |

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


## License

This project is licensed under the [MIT License](LICENSE).

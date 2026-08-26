"""The public project list.

One source for both /projects/ and the home page, which shows the first three.
Order is the display order — newest first — so reordering here reorders both.
"""

PROJECTS = (
    {
        "title": "My Personal Website",
        "url": "https://github.com/pflaumax/personal-website",
        # The Tools page is part of this project, so it is linked from here
        # rather than holding a slot in the primary nav.
        "demo_url": "/tools/",
        "demo_label": "Todo + Pomodoro demo",
        "description": (
            "Built with Django and Python, features a Tools page with a to-do "
            "list and Pomodoro timer (HTML/CSS/JS). It also includes a blog "
            "platform for personal posts and implements a fully responsive "
            "design for optimal viewing across all devices."
        ),
        "stack": ("Python", "Django", "JavaScript", "HTML/CSS", "GNU/Linux", "Git"),
    },
    {
        "title": "Event Manager",
        "url": "https://github.com/pflaumax/event_manager",
        "description": (
            "A Django-based Event Management System with two roles: Event "
            "Creators and Visitors. It simulates a real-world platform for "
            "managing and attending events, featuring role-based access, and "
            "email-based registration via a custom user model."
        ),
        "stack": ("Python", "Django", "REST API", "PostgreSQL", "Docker", "Git"),
    },
    {
        "title": "ESP32 Dashboard",
        "url": "https://github.com/pflaumax/esp32_dashboard",
        "description": (
            "A dashboard powered by the ESP32-WROOM and an E-paper display, "
            "showing the current date and time, weather conditions, views of my "
            "personal website, and blocked queries from Pi-hole on a Raspberry "
            "Pi."
        ),
        "stack": ("Python", "MicroPython", "REST API", "GNU/Linux", "Git", "ESP32", "Raspberry Pi"),
    },
    {
        "title": "FastAPI TODO List",
        "url": "https://github.com/pflaumax/fastapi_todo_list",
        "description": (
            "A simple TODO list application built with FastAPI. It uses an "
            "in-memory dictionary as a database, Pydantic models for data "
            "validation, and includes comprehensive unit tests. Example HTTP "
            "requests provided for testing."
        ),
        "stack": ("Python", "FastAPI", "Pydantic", "Pytest", "GNU/Linux", "Git"),
    },
    {
        "title": "GitHub User Fetcher",
        "url": "https://github.com/pflaumax/external_api_integration",
        "description": (
            "Fetches users from the GitHub API and saves them to a CSV file. "
            "FastAPI powered endpoints start tasks, Celery handles async "
            "processing, and Redis is used as the message broker. All services "
            "run in Docker containers."
        ),
        "stack": ("Python", "FastAPI", "Celery", "Redis", "Docker", "Git"),
    },
    {
        "title": "ML Task Predictor",
        "url": "https://github.com/pflaumax/simple_ml_integration",
        "description": (
            "ML-powered REST API that predicts the priority of tasks based on "
            "their descriptions using text classification. The FastAPI server "
            "exposes endpoints for predicting task priorities. Model is trained "
            "on a CSV dataset."
        ),
        "stack": ("Python", "FastAPI", "ML", "Data Processing", "Pandas", "Scikit Learn", "Git"),
    },
)

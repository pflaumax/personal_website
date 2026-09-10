"""The public project list.

One source for both /projects/ and the home page, which shows the first three.
Order is the display order — newest first — so reordering here reorders both.
"""

PROJECTS = (
    {
        "title": "Traffic Monitor",
        "url": "https://github.com/pflaumax/traffic_monitor",
        "description": (
            "A FastAPI reverse proxy with JWT auth that streams traffic "
            "events through Kafka, aggregates them into Redis for a live "
            "analytics dashboard, exposes an LLM /ask endpoint that answers "
            "questions in plain language grounded in the live stats, and "
            "ships an MCP server so an editor or AI assistant can query "
            "traffic directly."
        ),
        "stack": (
            "Python",
            "FastAPI",
            "MCP",
            "Kafka",
            "Redis",
            "Docker",
            "REST API",
            "Git",
        ),
    },
    {
        "title": "ML Task Predictor",
        "url": "https://github.com/pflaumax/simple_ml_integration",
        "description": (
            "A REST API built with FastAPI and machine learning that "
            "predicts task priority based on "
            "the task's description using text classification. The FastAPI "
            "server exposes endpoints for predicting task priorities. Model "
            "is trained on a CSV dataset."
        ),
        "stack": (
            "Python",
            "FastAPI",
            "ML",
            "Scikit Learn",
            "Data Processing",
            "Pandas",
            "Git",
        ),
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
        # Third-party write-ups. Both cover this one project, which is why they
        # sit on it rather than in the home page bio — a claim about your work
        # is worth most standing next to the work it is about.
        "press": (
            (
                "XDA Developers",
                "https://www.xda-developers.com/esp32-e-ink-display-dashboard/",
            ),
            (
                "Hackaday",
                "https://hackaday.com/2025/06/18/esp32-dashboard-is-a-great-way-to-stay-informed/",
            ),
        ),
        "stack": (
            "Python",
            "MicroPython",
            "REST API",
            "GNU/Linux",
            "Git",
            "ESP32",
            "Raspberry Pi",
        ),
    },
    {
        "title": "Status Checker",
        "url": "https://github.com/pflaumax/status_checker",
        "description": (
            "A Telegram bot and a watchdog script, run on a schedule by cron "
            "on a Raspberry Pi, that "
            "reports service, system, Docker, Pi-hole and network health, and "
            "sends alerts on outages or resource thresholds."
        ),
        "stack": (
            "Python",
            "Telegram API",
            "Raspberry Pi",
            "GNU/Linux",
            "Systemd",
            "Git",
        ),
    },
    {
        "title": "A Website on a .arpa Domain",
        "url": "https://github.com/pflaumax/arpa-joke",
        "description": (
            "A single-page site hosted on a reserved .arpa domain, claimed "
            "via a free IPv6 tunnel's reverse-DNS zone, themed as a "
            "Steins;Gate CERN terminal with a bilingual UI and small "
            "interactive easter eggs."
        ),
        "stack": ("HTML/CSS", "JavaScript", "DNS", "IPv6", "Git"),
    },
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
        "title": "Funko Bot",
        "url": "https://github.com/pflaumax/funko-bot",
        "description": (
            "A Bluesky bot that scrapes Funko.com for new releases, sales "
            "and restocks, filters out unwanted fandoms, and posts product "
            "updates with images on a schedule."
        ),
        "stack": (
            "Python",
            "Web Scraping",
            "Bluesky API",
            "Docker",
            "Git",
        ),
    },
    {
        "title": "HP Screens Bot",
        "url": "https://github.com/pflaumax/hp_screens_bot",
        "description": (
            "A Bluesky bot that posts random Harry Potter screengrabs every "
            "30 minutes, using face detection to prefer frames with "
            "characters and an optional trivia line from a Potter fact API."
        ),
        "stack": ("Python", "Image Processing", "Bluesky API", "Git"),
    },
    {
        "title": "Meetily Obsidian Scribe",
        "url": "https://github.com/pflaumax/meetily-obsidian-scribe",
        "description": (
            "A local sync tool that converts Meetily meeting recordings into "
            "Obsidian notes — frontmatter, transcript, summary and embedded "
            "audio — while preserving any content you edited by hand across "
            "re-syncs."
        ),
        "stack": ("Python", "Automation", "SQLite", "Obsidian", "Git"),
    },
    {
        "title": "FastAPI TODO List",
        "url": "https://github.com/pflaumax/fastapi_todo_list",
        "description": (
            "A simple TODO list application built with FastAPI. It uses a "
            "dictionary in memory as a database, Pydantic models for data "
            "validation, and includes comprehensive unit tests. Example HTTP "
            "requests provided for testing."
        ),
        "stack": ("Python", "FastAPI", "Pydantic", "Pytest", "GNU/Linux", "Git"),
    },
    {
        "title": "Event Manager",
        "url": "https://github.com/pflaumax/event_manager",
        "description": (
            "An Event Management System built with Django, with two roles: "
            "Event Creators and Visitors. It simulates a real-world platform for "
            "managing and attending events, featuring access control based on "
            "roles, and registration by email via a custom user model."
        ),
        "stack": ("Python", "Django", "REST API", "PostgreSQL", "Docker", "Git"),
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
)

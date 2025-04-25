import os
import django
from dotenv import load_dotenv


load_dotenv()

# Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "website_project.settings")
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

USERNAME = os.getenv("DJANGO_SUPERUSER_USERNAME")
EMAIL = os.getenv("DJANGO_SUPERUSER_EMAIL")
PASSWORD = os.getenv("DJANGO_SUPERUSER_PASSWORD")


def create_superuser():
    print("Creating superuser if needed...")

    if not all([USERNAME, EMAIL, PASSWORD]):
        print("Missing superuser ENV variables. Skipping creation.")
        return

    try:
        if not User.objects.filter(username=USERNAME).exists():
            User.objects.create_superuser(USERNAME, EMAIL, PASSWORD)
            print(f"Superuser '{USERNAME}' created successfully!")
        else:
            print(f"Superuser '{USERNAME}' already exists.")
    except Exception as e:
        print(f"Error creating superuser: {e}")


if __name__ == "__main__":
    create_superuser()

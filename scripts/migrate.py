import os
import subprocess
import sys

from dotenv import load_dotenv

# Add the project root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()


def run_migrations():
    print("Running migrations...")
    try:
        subprocess.check_call([sys.executable, "manage.py", "migrate"])
        print("Migrations completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Error running migrations: {e}")
        sys.exit(1)


def load_data():
    fixture_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data.json"
    )
    if not os.path.exists(fixture_path):
        print("No data.json fixture found, skipping data load.")
        return

    print("Loading data from data.json...")
    try:
        subprocess.check_call([sys.executable, "manage.py", "loaddata", "data.json"])
        print("Data loaded successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Error loading data: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_migrations()
    load_data()

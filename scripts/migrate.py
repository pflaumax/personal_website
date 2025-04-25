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


if __name__ == "__main__":
    run_migrations()

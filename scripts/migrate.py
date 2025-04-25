import os
import subprocess
import sys
from dotenv import load_dotenv

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

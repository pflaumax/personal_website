"""Take a restorable database backup — the rollback point docs/phase5 asks for.

    python scripts/backup_db.py [output-dir]

The obvious one-liner does not work here:

    pg_dump -d "$DATABASE_URL"

`DATABASE_URL` carries an unencoded `@` inside the password. Python's `urlsplit`
divides the userinfo at the *last* `@` and so guesses right, which is why Django
runs; libpq follows RFC 3986 and divides at the *first*, so `pg_dump` goes
looking for a host that is really the tail of the password. This parses the URL
in Python and hands `pg_dump` the parts as separate flags instead, which works
whether or not the password is ever percent-encoded.

Deliberately does not call `django.setup()`. A backup tool is most wanted when
the application will not boot, so it depends on nothing but the environment.

The password is passed through `PGPASSWORD` in the child environment and is
never printed or placed on a command line, where it would be visible in `ps`.
"""

import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# docs/phase5 says to check the dump is not empty before relying on it. A real
# dump of this database is tens of KB; anything this small means pg_dump wrote a
# header and then failed.
MIN_PLAUSIBLE_BYTES = 4096


def _timestamp():
    return datetime.now().strftime("%Y-%m-%d_%H%M")


def backup_sqlite(out_dir):
    """Dev path: the database is a single file, so copying it is the backup."""
    source = PROJECT_ROOT / "db.sqlite3"
    if not source.exists():
        sys.exit(f"No DATABASE_URL and no {source} — nothing to back up.")

    target = out_dir / f"backup_sqlite_{_timestamp()}.sqlite3"
    shutil.copy2(source, target)
    return target, f"cp {target} {source}"


def backup_postgres(url, out_dir):
    """Prod path: pg_dump in custom format, so pg_restore --clean can undo it."""
    parts = urlsplit(url)
    name = parts.path.lstrip("/")
    if not (parts.hostname and name):
        sys.exit("DATABASE_URL is missing a host or a database name.")

    target = out_dir / f"backup_{name}_{_timestamp()}.dump"
    command = [
        "pg_dump",
        "--format=custom",
        "--host",
        parts.hostname,
        "--port",
        str(parts.port or 5432),
        "--username",
        unquote(parts.username or ""),
        "--dbname",
        name,
        "--file",
        str(target),
    ]

    env = dict(os.environ)
    if parts.password:
        # Not on the command line: argv is world-readable through ps.
        env["PGPASSWORD"] = unquote(parts.password)

    try:
        result = subprocess.run(command, env=env, capture_output=True, text=True)
    except FileNotFoundError:
        sys.exit("pg_dump is not on PATH — install the postgresql-client package.")

    if result.returncode != 0:
        sys.exit(f"pg_dump failed:\n{result.stderr.strip()}")

    return target, f"pg_restore --clean --dbname {name} {target}"


def main():
    load_dotenv(PROJECT_ROOT / ".env")

    out_dir = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else Path.home()
    if len(sys.argv) > 2:
        sys.exit(__doc__)
    out_dir.mkdir(parents=True, exist_ok=True)

    url = os.environ.get("DATABASE_URL")
    if url:
        target, restore = backup_postgres(url, out_dir)
    else:
        target, restore = backup_sqlite(out_dir)

    size = target.stat().st_size
    print(f"{target}  ({size:,} bytes)")
    if size < MIN_PLAUSIBLE_BYTES:
        sys.exit(
            f"That is under {MIN_PLAUSIBLE_BYTES:,} bytes, which is too small to "
            "be a real dump of this database. Do not rely on it."
        )
    print(f"restore with:  {restore}")


if __name__ == "__main__":
    main()

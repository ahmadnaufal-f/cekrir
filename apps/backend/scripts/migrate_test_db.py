import os
from pathlib import Path
from urllib.parse import urlsplit

from alembic import command
from alembic.config import Config
from dotenv import load_dotenv

root = Path(__file__).resolve().parents[3]
load_dotenv(root / ".env")
test_url = os.getenv("TEST_DATABASE_URL")
if not test_url:
    raise SystemExit("Set TEST_DATABASE_URL before deploying test migrations")
parsed = urlsplit(test_url)
if parsed.scheme not in {
    "postgres",
    "postgresql",
    "postgresql+psycopg",
} or not parsed.path.endswith("_test"):
    raise SystemExit("TEST_DATABASE_URL must be PostgreSQL and end in _test")
app = urlsplit(os.getenv("DATABASE_URL", ""))
if (parsed.hostname, parsed.port or 5432, parsed.path) == (
    app.hostname,
    app.port or 5432,
    app.path,
):
    raise SystemExit("The test database must differ from the application database")

os.environ["DATABASE_URL"] = test_url
config = Config(str(root / "apps" / "backend" / "alembic.ini"))
command.upgrade(config, "head")

"""Settings for running the test suite against in-memory SQLite.

Usage:
    uv run pytest --ds=kofre.test_settings

The default settings point at the Docker Postgres service; this module swaps in
SQLite so the contract tests can run without any external service.
"""

from .settings import *  # noqa: F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

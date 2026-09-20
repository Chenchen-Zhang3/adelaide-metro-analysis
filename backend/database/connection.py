import os
import sqlite3
from pathlib import Path


DATABASE_PATH_ENVIRONMENT_VARIABLE = "ADELAIDE_METRO_DATABASE_PATH"
DEFAULT_DATABASE_PATH = Path(__file__).parent / "adelaide_metro.db"


def configured_database_path(environ=None):
    """Return the SQLite path configured for the running application."""
    environment = os.environ if environ is None else environ
    configured_path = environment.get(DATABASE_PATH_ENVIRONMENT_VARIABLE)

    if configured_path:
        return Path(configured_path)

    return DEFAULT_DATABASE_PATH


DATABASE_PATH = configured_database_path()


def get_connection():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection

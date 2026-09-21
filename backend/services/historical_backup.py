"""Create a consistent SQLite snapshot of the historical collector database."""

import argparse
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from backend.database.connection import configured_database_path


def default_backup_path(source_database, output_directory, timestamp=None):
    """Build a timestamped backup path without modifying the live database."""
    source_database = Path(source_database)
    output_directory = Path(output_directory)
    timestamp = timestamp or datetime.now()
    timestamp_text = timestamp.strftime("%Y%m%d_%H%M%S")
    return output_directory / (
        f"{source_database.stem}_{timestamp_text}{source_database.suffix}"
    )


def create_sqlite_backup(source_database, destination_database):
    """Use SQLite's online backup API to create a consistent snapshot."""
    source_database = Path(source_database).resolve()
    destination_database = Path(destination_database).resolve()

    if not source_database.is_file():
        raise FileNotFoundError(
            f"Historical SQLite database not found: {source_database}"
        )
    if source_database == destination_database:
        raise ValueError("Backup destination must differ from the live database")
    if destination_database.exists():
        raise FileExistsError(
            f"Backup destination already exists: {destination_database}"
        )

    destination_database.parent.mkdir(parents=True, exist_ok=True)
    source_uri = f"{source_database.as_uri()}?mode=ro"

    with closing(sqlite3.connect(source_uri, uri=True)) as source_connection:
        with closing(sqlite3.connect(destination_database)) as destination_connection:
            source_connection.backup(destination_connection)
            destination_connection.commit()

    with closing(sqlite3.connect(destination_database)) as backup_connection:
        integrity_result = backup_connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

    if integrity_result != "ok":
        raise sqlite3.DatabaseError(
            f"Backup integrity check failed: {integrity_result}"
        )

    return destination_database


def parse_arguments(arguments=None):
    parser = argparse.ArgumentParser(
        description="Create a consistent snapshot of the historical SQLite database."
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=configured_database_path(),
        help="Live SQLite database. Defaults to ADELAIDE_METRO_DATABASE_PATH.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data") / "backups",
        help="Directory for the timestamped snapshot.",
    )
    return parser.parse_args(arguments)


def main(arguments=None):
    options = parse_arguments(arguments)
    destination = default_backup_path(options.database, options.output_dir)
    completed_backup = create_sqlite_backup(options.database, destination)
    print(f"Historical database backup created: {completed_backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

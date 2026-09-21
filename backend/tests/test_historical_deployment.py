import logging
import os
import sqlite3
import tempfile
import unittest
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from backend.services.historical_backup import (
    create_sqlite_backup,
    default_backup_path,
)
from backend.services.historical_collection import (
    LOG_PATH_ENVIRONMENT_VARIABLE,
    STATIC_GTFS_PATH_ENVIRONMENT_VARIABLE,
    configured_log_path,
    create_logging_handlers,
    parse_arguments,
)
from backend.services.windows_single_instance import (
    HistoricalCollectorAlreadyRunningError,
    WindowsSingleInstanceGuard,
)


class TestHistoricalCollectorDeployment(unittest.TestCase):
    def test_static_gtfs_directory_can_come_from_environment(self):
        configured_path = Path("client-data") / "static_gtfs"
        with patch.dict(
            os.environ,
            {STATIC_GTFS_PATH_ENVIRONMENT_VARIABLE: str(configured_path)},
        ):
            options = parse_arguments([])

        self.assertEqual(options.static_gtfs_dir, configured_path)

    def test_cli_static_gtfs_directory_overrides_environment(self):
        with patch.dict(
            os.environ,
            {STATIC_GTFS_PATH_ENVIRONMENT_VARIABLE: "environment-static"},
        ):
            options = parse_arguments(
                ["--static-gtfs-dir", "command-line-static"]
            )

        self.assertEqual(
            options.static_gtfs_dir,
            Path("command-line-static"),
        )

    def test_log_path_can_come_from_environment(self):
        expected_path = Path("logs") / "historical_collector.log"
        with patch.dict(
            os.environ,
            {LOG_PATH_ENVIRONMENT_VARIABLE: str(expected_path)},
        ):
            self.assertEqual(configured_log_path(), expected_path)

    def test_rotating_file_handler_keeps_unattended_logs(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            log_path = Path(temporary_directory) / "logs" / "collector.log"
            handlers = create_logging_handlers(log_path)
            file_handler = handlers[1]
            test_logger = logging.getLogger(
                f"historical-deployment-test-{uuid.uuid4()}"
            )
            test_logger.setLevel(logging.INFO)
            test_logger.propagate = False
            test_logger.addHandler(file_handler)

            try:
                test_logger.info("collection cycle completed")
                file_handler.flush()
            finally:
                test_logger.removeHandler(file_handler)
                for handler in handlers:
                    handler.close()

            self.assertIn(
                "collection cycle completed",
                log_path.read_text(encoding="utf-8"),
            )

    def test_online_backup_contains_committed_historical_rows(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source_database = root / "historical.db"
            backup_database = root / "backups" / "historical_snapshot.db"

            source_connection = sqlite3.connect(source_database)
            try:
                source_connection.execute(
                    "CREATE TABLE vehicle_positions (vehicle_id TEXT)"
                )
                source_connection.execute(
                    "INSERT INTO vehicle_positions VALUES ('vehicle-1')"
                )
                source_connection.commit()
                completed_backup = create_sqlite_backup(
                    source_database,
                    backup_database,
                )
            finally:
                source_connection.close()

            backup_connection = sqlite3.connect(completed_backup)
            try:
                stored_vehicle = backup_connection.execute(
                    "SELECT vehicle_id FROM vehicle_positions"
                ).fetchone()[0]
            finally:
                backup_connection.close()

        self.assertEqual(stored_vehicle, "vehicle-1")

    def test_online_backup_rejects_missing_source_database(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            with self.assertRaises(FileNotFoundError):
                create_sqlite_backup(
                    root / "missing.db",
                    root / "backup.db",
                )

    def test_default_backup_path_is_timestamped(self):
        backup_path = default_backup_path(
            "data/historical/adelaide_metro_history.db",
            "data/backups",
            timestamp=datetime(2026, 9, 21, 14, 30, 5),
        )

        self.assertEqual(
            backup_path,
            Path("data/backups/adelaide_metro_history_20260921_143005.db"),
        )

    @unittest.skipUnless(os.name == "nt", "Windows mutex test")
    def test_windows_mutex_rejects_duplicate_collector_instance(self):
        mutex_name = f"AdelaideMetroCollectorTest-{uuid.uuid4()}"

        with WindowsSingleInstanceGuard(mutex_name):
            with self.assertRaises(HistoricalCollectorAlreadyRunningError):
                with WindowsSingleInstanceGuard(mutex_name):
                    self.fail("duplicate mutex should not be acquired")


if __name__ == "__main__":
    unittest.main()

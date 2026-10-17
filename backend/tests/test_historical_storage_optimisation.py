import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import backend.database.connection as database_connection
from backend.database.historical_storage import (
    configured_trip_update_checkpoint_seconds,
    derived_actual_arrival,
    epoch_to_adelaide_iso,
    iso_timestamp_to_epoch,
)
from backend.database.models import (
    HistoricalDatabaseUpgradeRequiredError,
    create_tables,
)
from backend.database.repository import (
    get_trip_updates,
    persist_realtime_collection,
)


class TestHistoricalStorageOptimisation(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.original_database_path = database_connection.DATABASE_PATH
        database_connection.DATABASE_PATH = (
            Path(self.temporary_directory.name) / "optimised.db"
        )
        create_tables()

    def tearDown(self):
        database_connection.DATABASE_PATH = self.original_database_path
        self.temporary_directory.cleanup()

    def trip_update(self, timestamp="2026-09-17T09:06:00+09:30", delay=360):
        scheduled = "2026-09-17T09:00:00+09:30"
        actual = datetime.fromisoformat(scheduled) + timedelta(seconds=delay)
        return {
            "trip_id": "TRIP_001",
            "route_id": "ROUTE_001",
            "stop_id": "STOP_001",
            "scheduled_arrival": scheduled,
            "actual_arrival": actual.isoformat(),
            "delay_seconds": delay,
            "timestamp": timestamp,
        }

    def count(self, table):
        connection = database_connection.get_connection()
        try:
            return connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        finally:
            connection.close()

    def test_unchanged_state_is_suppressed_but_cycle_is_recorded(self):
        first = self.trip_update()
        second = self.trip_update("2026-09-17T09:07:00+09:30")
        first_summary = persist_realtime_collection([], [first])
        second_summary = persist_realtime_collection([], [second])

        self.assertEqual(first_summary["trip_updates_initial"], 1)
        self.assertEqual(second_summary["trip_updates_inserted"], 0)
        self.assertEqual(second_summary["trip_updates_suppressed"], 1)
        self.assertEqual(self.count("trip_updates"), 1)
        self.assertEqual(self.count("collection_cycles"), 2)

    def test_changed_state_is_stored_immediately(self):
        persist_realtime_collection([], [self.trip_update()])
        changed = self.trip_update("2026-09-17T09:07:00+09:30", delay=420)
        summary = persist_realtime_collection([], [changed])

        self.assertEqual(summary["trip_updates_inserted"], 1)
        self.assertEqual(summary["trip_updates_changed"], 1)
        self.assertEqual(self.count("trip_updates"), 2)

    def test_periodic_checkpoint_is_stored_after_fifteen_minutes(self):
        persist_realtime_collection([], [self.trip_update()], checkpoint_seconds=900)
        still_unchanged = self.trip_update("2026-09-17T09:20:00+09:30")
        persist_realtime_collection(
            [], [still_unchanged], checkpoint_seconds=900
        )
        checkpoint = self.trip_update("2026-09-17T09:21:00+09:30")
        summary = persist_realtime_collection(
            [], [checkpoint], checkpoint_seconds=900
        )

        self.assertEqual(summary["trip_updates_checkpointed"], 1)
        self.assertEqual(self.count("trip_updates"), 2)

    def test_persisted_state_survives_repository_reopen(self):
        persist_realtime_collection([], [self.trip_update()])
        # Each persistence call opens a new connection, modelling process restart.
        unchanged = self.trip_update("2026-09-17T09:07:00+09:30")
        summary = persist_realtime_collection([], [unchanged])

        self.assertEqual(summary["trip_updates_inserted"], 0)
        self.assertEqual(self.count("trip_update_current_state"), 1)

    def test_reappearance_after_long_gap_is_stored(self):
        persist_realtime_collection([], [self.trip_update()], checkpoint_seconds=900)
        reappeared = self.trip_update("2026-09-17T09:22:00+09:30")
        summary = persist_realtime_collection(
            [], [reappeared], checkpoint_seconds=900
        )

        self.assertEqual(summary["trip_updates_reappeared"], 1)

    def test_integer_timestamp_round_trip_preserves_adelaide_offsets(self):
        for value in (
            "2026-09-17T09:06:00+09:30",
            "2026-12-17T09:06:00+10:30",
        ):
            self.assertEqual(
                epoch_to_adelaide_iso(iso_timestamp_to_epoch(value)),
                value,
            )

    def test_actual_arrival_is_derived_at_query_boundary(self):
        update = self.trip_update()
        persist_realtime_collection([], [update])

        stored = get_trip_updates(update["route_id"])[0]
        self.assertEqual(stored["actual_arrival"], update["actual_arrival"])
        self.assertEqual(stored["timestamp"], update["timestamp"])
        self.assertEqual(stored["observation_kind"], "initial")

    def test_inconsistent_actual_arrival_rolls_back_cycle(self):
        update = self.trip_update()
        update["actual_arrival"] = "2026-09-17T09:07:00+09:30"

        with self.assertRaises(sqlite3.IntegrityError):
            persist_realtime_collection([], [update])

        self.assertEqual(self.count("trip_updates"), 0)
        self.assertEqual(self.count("collection_cycles"), 0)

    def test_schema_uses_integer_time_and_consolidated_indexes(self):
        connection = database_connection.get_connection()
        try:
            columns = {
                row["name"]: row["type"]
                for row in connection.execute("PRAGMA table_info(trip_updates)")
            }
            indexes = {
                row["name"]
                for row in connection.execute("PRAGMA index_list(trip_updates)")
            }
        finally:
            connection.close()

        self.assertEqual(columns["scheduled_arrival"], "INTEGER")
        self.assertEqual(columns["observed_at"], "INTEGER")
        self.assertNotIn("actual_arrival", columns)
        self.assertNotIn("idx_trip_updates_route", indexes)
        self.assertIn("idx_trip_updates_filters", indexes)

    def test_legacy_schema_is_refused_without_in_place_changes(self):
        legacy_path = Path(self.temporary_directory.name) / "legacy.db"
        connection = sqlite3.connect(legacy_path)
        connection.execute(
            "CREATE TABLE trip_updates (id INTEGER PRIMARY KEY, actual_arrival TEXT, timestamp TEXT)"
        )
        connection.commit()
        connection.close()
        database_connection.DATABASE_PATH = legacy_path

        with self.assertRaises(HistoricalDatabaseUpgradeRequiredError):
            create_tables()

        connection = sqlite3.connect(legacy_path)
        try:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        finally:
            connection.close()
        self.assertEqual(tables, {"trip_updates"})

    def test_checkpoint_configuration_validation(self):
        self.assertEqual(
            configured_trip_update_checkpoint_seconds({}),
            900,
        )
        self.assertEqual(
            configured_trip_update_checkpoint_seconds(
                {"ADELAIDE_METRO_TRIP_UPDATE_CHECKPOINT_SECONDS": "300"}
            ),
            300,
        )
        with self.assertRaises(ValueError):
            configured_trip_update_checkpoint_seconds(
                {"ADELAIDE_METRO_TRIP_UPDATE_CHECKPOINT_SECONDS": "0"}
            )

    def test_derived_actual_arrival_helper(self):
        scheduled = iso_timestamp_to_epoch("2026-09-17T09:00:00+09:30")
        self.assertEqual(
            derived_actual_arrival(scheduled, 360),
            "2026-09-17T09:06:00+09:30",
        )


if __name__ == "__main__":
    unittest.main()

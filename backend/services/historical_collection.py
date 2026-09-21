"""CLI startup for continuous GTFS-Realtime historical collection."""

import argparse
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from backend.database.models import create_tables
from backend.parsers.static_gtfs import parse_stop_times
from backend.realtime.pipeline import GTFSRealtimeProcessingPipeline
from backend.services.gtfs_converter import build_stop_time_index
from backend.services.pipeline import run_collection_and_persist
from backend.services.windows_single_instance import (
    HistoricalCollectorAlreadyRunningError,
    WindowsSingleInstanceGuard,
)


logger = logging.getLogger(__name__)
STATIC_GTFS_PATH_ENVIRONMENT_VARIABLE = "ADELAIDE_METRO_STATIC_GTFS_PATH"
LOG_PATH_ENVIRONMENT_VARIABLE = "ADELAIDE_METRO_LOG_PATH"
WINDOWS_MUTEX_NAME = "AdelaideMetroHistoricalCollector"


def configured_static_gtfs_path(environ=None):
    """Return the configured static GTFS directory, if provided."""
    environment = os.environ if environ is None else environ
    configured_path = environment.get(STATIC_GTFS_PATH_ENVIRONMENT_VARIABLE)
    return Path(configured_path) if configured_path else None


def configured_log_path(environ=None):
    """Return the optional unattended-operation log path."""
    environment = os.environ if environ is None else environ
    configured_path = environment.get(LOG_PATH_ENVIRONMENT_VARIABLE)
    return Path(configured_path) if configured_path else None


def create_logging_handlers(log_path=None):
    """Create console logging plus an optional bounded rotating file log."""
    handlers = [logging.StreamHandler()]

    if log_path is not None:
        log_path = Path(log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(
            RotatingFileHandler(
                log_path,
                maxBytes=5 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8",
            )
        )

    return handlers


def load_stop_time_index(static_gtfs_directory):
    """Load and index static stop times once during application startup."""
    static_gtfs_directory = Path(static_gtfs_directory)
    stop_times_path = static_gtfs_directory / "stop_times.txt"
    stop_times = parse_stop_times(stop_times_path)
    stop_time_index = build_stop_time_index(stop_times)
    logger.info(
        "Loaded %d static stop-time records into an index with %d keys",
        len(stop_times),
        len(stop_time_index),
    )
    return stop_time_index


class HistoricalCollectionRunner:
    """Initialise dependencies once, then reuse the existing collection loop."""

    def __init__(
        self,
        static_gtfs_directory,
        pipeline_factory=GTFSRealtimeProcessingPipeline,
        create_tables_function=create_tables,
        index_loader=load_stop_time_index,
    ):
        self.static_gtfs_directory = Path(static_gtfs_directory)
        self.pipeline_factory = pipeline_factory
        self.create_tables_function = create_tables_function
        self.index_loader = index_loader
        self.pipeline = None

    def initialise(self):
        """Prepare static lookup, schema and realtime pipeline once."""
        if self.pipeline is not None:
            return self.pipeline

        logger.info(
            "Initialising historical GTFS collector with static data from %s",
            self.static_gtfs_directory,
        )
        stop_time_index = self.index_loader(self.static_gtfs_directory)
        self.create_tables_function()
        self.pipeline = self.pipeline_factory(stop_time_index=stop_time_index)
        logger.info("Historical GTFS collector initialised")
        return self.pipeline

    def run(self, max_cycles=None, sleep_function=None, stop_event=None):
        """Run the existing persistence-aware scheduler with one shared index."""
        pipeline = self.initialise()
        arguments = {
            "max_cycles": max_cycles,
            "stop_event": stop_event,
        }
        if sleep_function is not None:
            arguments["sleep_function"] = sleep_function
        return run_collection_and_persist(pipeline.collector, **arguments)


def _positive_cycle_count(value):
    try:
        parsed_value = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "max cycles must be an integer"
        ) from error

    if parsed_value <= 0:
        raise argparse.ArgumentTypeError("max cycles must be greater than zero")
    return parsed_value


def parse_arguments(arguments=None):
    parser = argparse.ArgumentParser(
        description="Continuously collect Adelaide Metro GTFS-Realtime history."
    )
    parser.add_argument(
        "--static-gtfs-dir",
        default=configured_static_gtfs_path(),
        type=Path,
        help=(
            "Directory containing the current static GTFS stop_times.txt file. "
            f"Defaults to {STATIC_GTFS_PATH_ENVIRONMENT_VARIABLE}."
        ),
    )
    parser.add_argument(
        "--max-cycles",
        type=_positive_cycle_count,
        help="Run a finite number of cycles for a controlled pilot.",
    )
    options = parser.parse_args(arguments)
    if options.static_gtfs_dir is None:
        parser.error(
            "--static-gtfs-dir or "
            f"{STATIC_GTFS_PATH_ENVIRONMENT_VARIABLE} is required"
        )
    return options


def main(arguments=None):
    """Run the collector and convert Ctrl+C into a clean shutdown message."""
    options = parse_arguments(arguments)
    log_path = configured_log_path()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=create_logging_handlers(log_path),
        force=True,
    )
    runner = HistoricalCollectionRunner(options.static_gtfs_dir)

    try:
        with WindowsSingleInstanceGuard(WINDOWS_MUTEX_NAME):
            logger.info(
                "Historical GTFS collector starting%s",
                f"; file log: {log_path}" if log_path else "",
            )
            runner.run(max_cycles=options.max_cycles)
            logger.info("Historical GTFS collector stopped normally")
    except HistoricalCollectorAlreadyRunningError as error:
        logger.error("%s", error)
        return 2
    except KeyboardInterrupt:
        logger.info("Historical GTFS collector stopped by user")
    except Exception:
        logger.exception("Historical GTFS collector stopped after a fatal error")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

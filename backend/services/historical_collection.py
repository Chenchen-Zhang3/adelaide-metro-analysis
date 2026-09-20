"""CLI startup for continuous GTFS-Realtime historical collection."""

import argparse
import logging
from pathlib import Path

from backend.database.models import create_tables
from backend.parsers.static_gtfs import parse_stop_times
from backend.realtime.pipeline import GTFSRealtimeProcessingPipeline
from backend.services.gtfs_converter import build_stop_time_index
from backend.services.pipeline import run_collection_and_persist


logger = logging.getLogger(__name__)


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
        required=True,
        type=Path,
        help="Directory containing the current static GTFS stop_times.txt file.",
    )
    parser.add_argument(
        "--max-cycles",
        type=_positive_cycle_count,
        help="Run a finite number of cycles for a controlled pilot.",
    )
    return parser.parse_args(arguments)


def main(arguments=None):
    """Run the collector and convert Ctrl+C into a clean shutdown message."""
    options = parse_arguments(arguments)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    runner = HistoricalCollectionRunner(options.static_gtfs_dir)

    try:
        runner.run(max_cycles=options.max_cycles)
    except KeyboardInterrupt:
        logger.info("Historical GTFS collector stopped by user")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

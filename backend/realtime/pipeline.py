"""Reusable GTFS-Realtime ingestion workflow that stops before persistence.

The workflow returns the database-ready historical record dictionaries already
produced by the realtime collector. Database insertion belongs to the wider
system-integration layer in ``backend.services.pipeline``. Service Alerts are
not included because the project does not yet define a historical record
contract for them.
"""

from time import sleep

from backend.realtime.client import GTFSRealtimeClient
from backend.realtime.collector import GTFSRealtimeCollector


class GTFSRealtimeProcessingPipeline:
    """Expose one reusable entry point for a complete realtime processing cycle.

    ``client`` and ``sleep_function`` are injectable for tests or alternative
    runtimes. ``stop_time_index`` is created from static GTFS data outside this
    workflow and reused for every Trip Update cycle.
    """

    def __init__(
        self,
        client=None,
        stop_time_index=None,
        sleep_function=sleep,
    ):
        self.collector = GTFSRealtimeCollector(
            client=client or GTFSRealtimeClient(),
            stop_time_index=stop_time_index,
            sleep_function=sleep_function,
        )

    def process_once(self):
        """Return database-ready records for one Vehicle and Trip Update cycle."""
        return self.collector.collect_once()

    def run(self, max_cycles=None):
        """Run scheduled processing cycles using the configured polling policy."""
        return self.collector.run(max_cycles=max_cycles)

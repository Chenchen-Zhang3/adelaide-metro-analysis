import logging

from google.transit import gtfs_realtime_pb2
from google.protobuf.message import DecodeError


logger = logging.getLogger(__name__)


def decode_feed(data):
    if not isinstance(data, bytes):
        logger.error("GTFS-Realtime decoding failed: data is not bytes")
        raise TypeError("GTFS-Realtime data must be bytes")

    if not data:
        logger.error("GTFS-Realtime decoding failed: data is empty")
        raise ValueError("GTFS-Realtime data is empty")

    feed = gtfs_realtime_pb2.FeedMessage()

    try:
        feed.ParseFromString(data)
    except DecodeError as error:
        logger.error("GTFS-Realtime protobuf decoding failed")
        raise ValueError(
            "Failed to decode GTFS-Realtime protobuf data"
        ) from error

    logger.debug("Decoded GTFS-Realtime feed with %d entities", len(feed.entity))
    return feed

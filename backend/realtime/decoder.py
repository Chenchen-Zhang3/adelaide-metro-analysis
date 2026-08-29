from google.transit import gtfs_realtime_pb2
from google.protobuf.message import DecodeError


def decode_feed(data):
    if not isinstance(data, bytes):
        raise TypeError("GTFS-Realtime data must be bytes")

    if not data:
        raise ValueError("GTFS-Realtime data is empty")

    feed = gtfs_realtime_pb2.FeedMessage()

    try:
        feed.ParseFromString(data)
    except DecodeError as error:
        raise ValueError(
            "Failed to decode GTFS-Realtime protobuf data"
        ) from error

    return feed
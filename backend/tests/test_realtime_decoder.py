import unittest

from google.transit import gtfs_realtime_pb2

from backend.realtime.decoder import decode_feed


class TestGTFSRealtimeDecoder(unittest.TestCase):

    def create_valid_feed_bytes(self):
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "1.0"

        entity = feed.entity.add()
        entity.id = "test-entity"

        return feed.SerializeToString()

    def test_decode_valid_feed(self):
        data = self.create_valid_feed_bytes()

        feed = decode_feed(data)

        self.assertEqual(feed.header.gtfs_realtime_version, "1.0")
        self.assertEqual(len(feed.entity), 1)
        self.assertEqual(feed.entity[0].id, "test-entity")

    def test_decode_rejects_non_bytes(self):
        with self.assertRaises(TypeError):
            decode_feed("not-bytes")

    def test_decode_rejects_empty_bytes(self):
        with self.assertRaises(ValueError):
            decode_feed(b"")

    def test_decode_rejects_invalid_protobuf(self):
        with self.assertRaises(ValueError):
            decode_feed(b"\xff\xff\xff\xff")


if __name__ == "__main__":
    unittest.main()
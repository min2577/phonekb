import json
import unittest

from spp_protocol import MAGIC, MAX_PAYLOAD, PacketParser, ProtocolError, encode_packet


class SPPProtocolTests(unittest.TestCase):
    def test_fragmented_unicode_packet(self):
        raw = json.dumps(
            {"action": "type", "text": "中文输入🙂"}, ensure_ascii=False
        ).encode("utf-8")
        packet = encode_packet(raw)
        parser = PacketParser()
        out = []
        for byte in packet:
            out.extend(parser.feed(bytes([byte])))
        self.assertEqual(out, [raw])

    def test_coalesced_packets(self):
        first = b'{"action":"ping"}'
        second = b'{"action":"reload_layouts"}'
        parser = PacketParser()
        self.assertEqual(
            parser.feed(encode_packet(first) + encode_packet(second)),
            [first, second],
        )

    def test_recovers_after_noise_and_invalid_length(self):
        valid = b'{"action":"ping"}'
        corrupt = MAGIC + (MAX_PAYLOAD + 1).to_bytes(4, "big") + b"bad"
        parser = PacketParser()
        self.assertEqual(parser.feed(b"noise" + corrupt + encode_packet(valid)), [valid])

    def test_rejects_empty_and_oversized_payloads(self):
        with self.assertRaises(ProtocolError):
            encode_packet(b"")
        with self.assertRaises(ProtocolError):
            encode_packet(b"x" * (MAX_PAYLOAD + 1))


if __name__ == "__main__":
    unittest.main()

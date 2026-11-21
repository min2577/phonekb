"""PhoneKB SPP v2 stream framing.

RFCOMM is a byte stream, so Bluetooth packet boundaries must not be used as
message boundaries. Each packet is an eight-byte header followed by UTF-8
JSON: ``PKB2`` + unsigned big-endian payload length + payload.
"""

import struct
from typing import List


MAGIC = b"PKB2"
HEADER_SIZE = 8
MAX_PAYLOAD = 256 * 1024


class ProtocolError(ValueError):
    pass


def encode_packet(payload: bytes) -> bytes:
    if not isinstance(payload, (bytes, bytearray)):
        raise TypeError("payload must be bytes")
    size = len(payload)
    if size <= 0 or size > MAX_PAYLOAD:
        raise ProtocolError(f"invalid SPP payload length: {size}")
    return MAGIC + struct.pack(">I", size) + bytes(payload)


class PacketParser:
    """Incrementally parse packets and recover after unrelated/corrupt bytes."""

    def __init__(self, max_payload: int = MAX_PAYLOAD):
        self.max_payload = int(max_payload)
        self._buffer = bytearray()

    def reset(self) -> None:
        self._buffer.clear()

    def feed(self, chunk: bytes) -> List[bytes]:
        if chunk:
            self._buffer.extend(chunk)

        packets = []
        while True:
            start = self._buffer.find(MAGIC)
            if start < 0:
                # Keep a possible partial magic prefix for the next read.
                if len(self._buffer) > len(MAGIC) - 1:
                    del self._buffer[: -(len(MAGIC) - 1)]
                break
            if start:
                del self._buffer[:start]
            if len(self._buffer) < HEADER_SIZE:
                break

            size = struct.unpack(">I", self._buffer[4:8])[0]
            if size <= 0 or size > self.max_payload:
                # Drop one byte rather than the whole buffer so a following
                # valid magic can still be found.
                del self._buffer[0]
                continue
            packet_size = HEADER_SIZE + size
            if len(self._buffer) < packet_size:
                break
            packets.append(bytes(self._buffer[HEADER_SIZE:packet_size]))
            del self._buffer[:packet_size]
        return packets

import json
import unittest
from unittest import mock

import spp_bridge
from spp_protocol import PacketParser


class _FakeSerial:
    def __init__(self):
        self.writes = []
        self.closed = False

    def write(self, data):
        self.writes.append(bytes(data))
        return len(data)

    def flush(self):
        pass

    def close(self):
        self.closed = True


class SPPBridgeTests(unittest.TestCase):
    def test_ping_registers_session_and_returns_pong(self):
        dispatcher = spp_bridge._AsyncDispatcher()
        serial_port = _FakeSerial()
        session = spp_bridge.SPPSession("COM_TEST", "test incoming port")
        session.attach(serial_port)
        try:
            spp_bridge._handle_payload(
                dispatcher,
                session,
                json.dumps({"action": "ping", "protocol": 2}).encode("utf-8"),
            )
            self.assertTrue(session.registered)
            self.assertTrue(serial_port.writes)
            payloads = PacketParser().feed(b"".join(serial_port.writes))
            messages = [json.loads(payload.decode("utf-8")) for payload in payloads]
            self.assertEqual(messages, [{"action": "pong"}])
        finally:
            dispatcher.submit(spp_bridge._unregister_session(session))
            dispatcher.close()

    def test_mouse_move_uses_inline_no_ack_fast_path(self):
        class _NoDispatch:
            def submit(self, *args, **kwargs):
                raise AssertionError("mouse move should not enter the asyncio dispatcher")

        serial_port = _FakeSerial()
        session = spp_bridge.SPPSession("COM_TEST", "test incoming port")
        session.attach(serial_port)
        session.registered = True
        with mock.patch.object(spp_bridge.usb_server.mouse, "move", return_value=1) as move:
            spp_bridge._handle_payload(
                _NoDispatch(),
                session,
                json.dumps({"action": "mouse", "op": "move", "dx": 7, "dy": -3}).encode("utf-8"),
            )
        move.assert_called_once_with(7, -3)
        self.assertEqual(serial_port.writes, [])

    def test_legacy_mouse_move_gets_immediate_backpressure_ack(self):
        class _NoDispatch:
            def submit(self, *args, **kwargs):
                raise AssertionError("legacy mouse ACK should stay on the serial thread")

        serial_port = _FakeSerial()
        session = spp_bridge.SPPSession("COM_TEST", "test incoming port")
        session.attach(serial_port)
        session.registered = True
        with mock.patch.object(spp_bridge.usb_server.mouse, "move", return_value=1) as move:
            spp_bridge._handle_payload(
                _NoDispatch(),
                session,
                json.dumps({
                    "action": "mouse", "op": "move", "dx": 5, "dy": 2, "mouse_seq": 17,
                }).encode("utf-8"),
            )
        move.assert_called_once_with(5, 2)
        payloads = PacketParser().feed(b"".join(serial_port.writes))
        messages = [json.loads(payload.decode("utf-8")) for payload in payloads]
        self.assertEqual(messages, [{"action": "mouse_move_ack", "mouse_seq": 17}])


if __name__ == "__main__":
    unittest.main()

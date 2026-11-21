import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import adb_tunnel


class AdbTunnelTest(unittest.TestCase):
    def test_parse_devices_keeps_authorization_state(self):
        output = "List of devices attached\nGT6-1\tdevice product:realme\nGT6-2\tunauthorized\n\n"
        self.assertEqual(adb_tunnel.parse_adb_devices(output), {
            "GT6-1": "device",
            "GT6-2": "unauthorized",
        })

    def test_configured_adb_has_priority(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = Path(directory) / "adb.exe"
            adb.touch()
            with mock.patch.dict(os.environ, {"PHONEKB_ADB": str(adb)}):
                self.assertEqual(adb_tunnel.find_adb(), adb.resolve())

    def test_online_device_gets_reverse_mapping(self):
        monitor = adb_tunnel.AdbReverseMonitor(interval=1, refresh_interval=10)
        monitor._adb = Path("adb.exe")
        completed = mock.Mock(returncode=0, stdout="", stderr="")
        with mock.patch.object(adb_tunnel, "_run", return_value=completed) as run:
            monitor._update_devices({"GT6": "device"})
            monitor._update_devices({"GT6": "device"})
        run.assert_called_once_with(
            Path("adb.exe"), ["-s", "GT6", "reverse", "tcp:9877", "tcp:9877"]
        )


if __name__ == "__main__":
    unittest.main()

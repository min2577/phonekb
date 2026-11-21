"""Keep the Android USB reverse tunnel available while PhoneKB is running."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Iterable, Optional


log = logging.getLogger("phonekb.adb")
USB_PORT = 9877


def _candidate_paths() -> Iterable[Path]:
    configured = os.environ.get("PHONEKB_ADB")
    if configured:
        yield Path(configured)

    base = Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve().parent
    yield base / "adb.exe"
    yield base / "tools" / "adb.exe"

    for name in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        root = os.environ.get(name)
        if root:
            yield Path(root) / "platform-tools" / "adb.exe"

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        yield Path(local_app_data) / "Android" / "Sdk" / "platform-tools" / "adb.exe"

    # HBuilderX ships adb here. Search only common install/download roots so
    # startup never performs an unbounded drive-wide scan.
    hbuilder_roots = [
        Path("C:/Program Files/HBuilderX"),
    ]
    for root in hbuilder_roots:
        if not root.exists():
            continue
        direct = root / "plugins" / "launcher-tools" / "tools" / "adbs" / "adb.exe"
        yield direct
        try:
            yield from root.glob("HBuilderX*/HBuilderX/plugins/launcher-tools/tools/adbs/adb.exe")
        except OSError:
            pass


def find_adb() -> Optional[Path]:
    seen = set()
    for candidate in _candidate_paths():
        try:
            resolved = candidate.expanduser().resolve()
        except OSError:
            continue
        key = str(resolved).lower()
        if key in seen:
            continue
        seen.add(key)
        if resolved.is_file():
            return resolved
    found = shutil.which("adb")
    return Path(found).resolve() if found else None


def parse_adb_devices(output: str) -> dict[str, str]:
    devices: dict[str, str] = {}
    for raw in output.splitlines():
        line = raw.strip()
        if not line or line.startswith("List of devices attached") or "\t" not in line:
            continue
        serial, status = line.split("\t", 1)
        devices[serial.strip()] = status.strip().split()[0]
    return devices


def _run(adb: Path, args: list[str], timeout: float = 8.0) -> subprocess.CompletedProcess[str]:
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.run(
        [str(adb), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        creationflags=creationflags,
        check=False,
    )


class AdbReverseMonitor:
    def __init__(self, interval: float = 2.5, refresh_interval: float = 12.0):
        self.interval = max(1.0, float(interval))
        self.refresh_interval = max(self.interval, float(refresh_interval))
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._adb: Optional[Path] = None
        self._last_statuses: dict[str, str] = {}
        self._last_reverse: dict[str, float] = {}

    def start(self) -> bool:
        if self._thread and self._thread.is_alive():
            return True
        self._adb = find_adb()
        if not self._adb:
            log.warning("未找到 adb；USB 自动连接不可用。可设置 PHONEKB_ADB 指向 adb.exe")
            return False
        log.info("USB 自动隧道使用 adb: %s", self._adb)
        self._stop.clear()
        self._thread = threading.Thread(target=self._monitor, name="phonekb-adb-reverse", daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        self._stop.set()

    def _monitor(self) -> None:
        assert self._adb is not None
        while not self._stop.is_set():
            try:
                result = _run(self._adb, ["devices"])
                if result.returncode != 0:
                    log.warning("adb devices 失败: %s", (result.stderr or result.stdout).strip())
                else:
                    self._update_devices(parse_adb_devices(result.stdout))
            except (OSError, subprocess.SubprocessError) as exc:
                log.warning("ADB USB 检查失败: %s", exc)
            self._stop.wait(self.interval)

    def _update_devices(self, statuses: dict[str, str]) -> None:
        if statuses != self._last_statuses:
            for serial, status in statuses.items():
                if status == "unauthorized":
                    log.warning("USB 手机 %s 等待授权，请在手机上允许 USB 调试", serial)
                elif status == "offline":
                    log.info("USB 手机 %s 当前离线", serial)
            self._last_statuses = dict(statuses)

        now = time.monotonic()
        online = {serial for serial, status in statuses.items() if status == "device"}
        for serial in list(self._last_reverse):
            if serial not in online:
                self._last_reverse.pop(serial, None)
        for serial in online:
            if now - self._last_reverse.get(serial, 0.0) < self.refresh_interval:
                continue
            result = _run(self._adb, ["-s", serial, "reverse", f"tcp:{USB_PORT}", f"tcp:{USB_PORT}"])
            if result.returncode == 0:
                first = serial not in self._last_reverse
                self._last_reverse[serial] = now
                if first:
                    log.info("USB 隧道已就绪: %s tcp:%s", serial, USB_PORT)
            else:
                log.warning("USB 隧道建立失败 %s: %s", serial, (result.stderr or result.stdout).strip())

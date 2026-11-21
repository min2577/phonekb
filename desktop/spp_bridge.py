#!/usr/bin/env python3
"""Classic Bluetooth RFCOMM (SPP) bridge for PhoneKB.

The Android app connects to a Windows incoming Bluetooth COM port. This
module turns the serial byte stream into JSON messages and reuses the USB
business-message handler.
"""

import asyncio
import json
import logging
import os
import threading
import time
from typing import Optional

import serial

import usb_server
from spp_protocol import PacketParser, ProtocolError, encode_packet

try:
    from serial.tools import list_ports
except ImportError:
    list_ports = None


log = logging.getLogger("phonekb.spp_bridge")
_CONFIG_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.dirname(os.path.abspath(__file__))),
    "PhoneKB",
)
_CONFIG_FILE = os.path.join(_CONFIG_DIR, "spp_config.json")
_RX_TIMEOUT_SECONDS = 40


def _find_bluetooth_ports():
    """Return Bluetooth serial ports with an incoming-port confidence flag."""
    found = []
    if list_ports is None:
        return found
    for port in list_ports.comports():
        description = port.description or ""
        manufacturer = port.manufacturer or ""
        hwid = port.hwid or ""
        searchable = " ".join((description, manufacturer, hwid)).lower()
        if "bluetooth" not in searchable and "蓝牙" not in searchable:
            continue
        upper_hwid = hwid.upper()
        incoming = (
            "_LOCALMFG&0000" in upper_hwid
            or "000000000000_00000000" in upper_hwid
        )
        found.append({
            "device": port.device,
            "description": description or manufacturer or "Bluetooth SPP",
            "hwid": hwid,
            "incoming": incoming,
        })
    return found


def _configured_port_name() -> str:
    env_port = os.environ.get("PHONEKB_SPP_PORT", "").strip()
    if env_port:
        return env_port
    try:
        with open(_CONFIG_FILE, "r", encoding="utf-8") as handle:
            return str(json.load(handle).get("port", "")).strip()
    except (OSError, ValueError, TypeError):
        return ""


def _save_port_name(port_name: str) -> None:
    try:
        os.makedirs(_CONFIG_DIR, exist_ok=True)
        with open(_CONFIG_FILE, "w", encoding="utf-8") as handle:
            json.dump({"port": port_name}, handle, ensure_ascii=False, indent=2)
    except OSError as error:
        log.warning("SPP 保存串口选择失败: %s", error)


def _select_bluetooth_port(candidates):
    if not candidates:
        return None
    configured = _configured_port_name().lower()
    if configured:
        for candidate in candidates:
            if candidate["device"].lower() == configured:
                return candidate
        log.warning("SPP 已保存串口 %s 当前不存在，将重新选择", configured)

    incoming = [candidate for candidate in candidates if candidate["incoming"]]
    selected = incoming[0] if incoming else candidates[0]
    _save_port_name(selected["device"])
    return selected


class _AsyncDispatcher:
    """Keep one asyncio loop alive for usb_server and background callbacks."""

    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self._started = threading.Event()
        self.thread = threading.Thread(target=self._run, name="spp-async", daemon=True)
        self.thread.start()
        self._started.wait(timeout=5)

    def _run(self):
        asyncio.set_event_loop(self.loop)
        self._started.set()
        self.loop.run_forever()

    def submit(self, coroutine, timeout=60):
        future = asyncio.run_coroutine_threadsafe(coroutine, self.loop)
        return future.result(timeout=timeout)

    def close(self):
        if self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(timeout=5)
        if not self.loop.is_running() and not self.loop.is_closed():
            self.loop.close()


class SPPSession:
    """WebSocket-shaped adapter used by usb_server._process_msg."""

    def __init__(self, port_name: str, description: str = ""):
        self.port_name = port_name
        self.description = description
        self.remote_address = ("spp", description or port_name)
        self.closed = False
        self.registered = False
        self.last_rx = time.monotonic()
        self._tx_lock = threading.Lock()
        self._serial: Optional[serial.Serial] = None

    def attach(self, serial_port: serial.Serial):
        self._serial = serial_port

    async def send(self, json_text: str):
        self.send_now(json_text)

    def send_now(self, json_text: str):
        if self.closed or self._serial is None:
            return
        try:
            packet = encode_packet(json_text.encode("utf-8"))
        except (UnicodeError, ProtocolError) as error:
            log.warning("SPP encode failed: %s", error)
            return
        with self._tx_lock:
            if self.closed or self._serial is None:
                return
            try:
                written = self._serial.write(packet)
                self._serial.flush()
                if written != len(packet):
                    raise serial.SerialException(
                        f"partial SPP write: {written}/{len(packet)}"
                    )
            except Exception as error:
                log.warning("SPP write failed: %s", error)
                self.closed = True
                try:
                    self._serial.close()
                except Exception:
                    pass

    async def close(self):
        self.closed = True
        if self._serial is not None:
            try:
                self._serial.close()
            except Exception:
                pass


async def _register_session(session: SPPSession):
    if session.registered:
        return
    usb_server._usb_sessions[session] = {
        "ip": "spp-local",
        "paired_at": time.time(),
    }
    usb_server._usb_targets.setdefault(session, 0)
    usb_server._register_codex_client(session)
    usb_server._fire_on_pair()
    session.registered = True
    log.info("SPP 手机握手成功: %s", session.port_name)


async def _unregister_session(session: SPPSession):
    try:
        usb_server.server._release_gamepad_keys(session)
        usb_server.keytrigger.key_up("rctrl")
    except Exception:
        pass
    usb_server._unregister_codex_client(session)
    usb_server._usb_sessions.pop(session, None)
    usb_server._usb_targets.pop(session, None)
    session.registered = False
    await session.close()


def _handle_payload(dispatcher: _AsyncDispatcher, session: SPPSession, payload: bytes):
    try:
        message = json.loads(payload.decode("utf-8"))
    except (UnicodeError, ValueError) as error:
        log.warning("SPP JSON 解析失败: %s | raw=%r", error, payload[:64])
        return
    if not isinstance(message, dict):
        log.warning("SPP 忽略非对象消息")
        return

    session.last_rx = time.monotonic()
    try:
        if not session.registered:
            dispatcher.submit(_register_session(session), timeout=10)
        action = message.get("action", "?")
        if action == "mouse" and message.get("op") == "move":
            # Relative moves are high-rate and need no response. Processing
            # them inline prevents stale motion from accumulating behind the
            # asyncio dispatcher and avoids per-frame INFO logging.
            usb_server.mouse.move(int(message.get("dx", 0)), int(message.get("dy", 0)))
            mouse_seq = message.get("mouse_seq")
            if mouse_seq is not None:
                session.send_now(json.dumps({"action": "mouse_move_ack", "mouse_seq": mouse_seq}))
            return
        log.info("SPP action=%s", action)
        dispatcher.submit(usb_server._process_msg(session, message))
    except Exception as error:
        log.exception("SPP 业务消息处理失败: %s", error)


def run_spp_server():
    log.info("SPP bridge v2 启动，等待 Windows 蓝牙入站串口")
    dispatcher = _AsyncDispatcher()
    retry_delay = 3

    while True:
        candidates = _find_bluetooth_ports()
        selected = _select_bluetooth_port(candidates)
        if selected is None:
            log.warning("SPP 未发现蓝牙 COM 端口，%d 秒后重试", retry_delay)
            time.sleep(retry_delay)
            continue

        if len(candidates) > 1:
            summary = [
                f"{item['device']} ({'入站' if item['incoming'] else '未确认'})"
                for item in candidates
            ]
            log.info("SPP 候选串口: %s；选择 %s", summary, selected["device"])

        port_name = selected["device"]
        description = selected["description"]
        log.info("SPP 打开 %s (%s)", port_name, description)
        try:
            serial_port = serial.Serial(port_name, baudrate=115200, timeout=1, write_timeout=10)
        except Exception as error:
            log.warning("SPP 打开 %s 失败: %s，%d 秒后重试", port_name, error, retry_delay)
            time.sleep(retry_delay)
            continue

        parser = PacketParser()
        session = SPPSession(port_name, description)
        session.attach(serial_port)
        log.info("SPP %s 已就绪，等待手机连接", port_name)

        try:
            while not session.closed:
                chunk = serial_port.read(4096)
                if not chunk:
                    if session.registered and time.monotonic() - session.last_rx > _RX_TIMEOUT_SECONDS:
                        log.warning("SPP 心跳超时，重置 %s", port_name)
                        break
                    continue
                for payload in parser.feed(chunk):
                    _handle_payload(dispatcher, session, payload)
        except serial.SerialException as error:
            log.warning("SPP 串口异常: %s", error)
        except Exception:
            log.exception("SPP 读取循环异常")
        finally:
            try:
                dispatcher.submit(_unregister_session(session), timeout=10)
            except Exception as error:
                log.warning("SPP session 清理失败: %s", error)
            try:
                serial_port.close()
            except Exception:
                pass
        log.info("SPP %s 已断开，%d 秒后重新监听", port_name, retry_delay)
        time.sleep(retry_delay)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    run_spp_server()

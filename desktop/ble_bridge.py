#!/usr/bin/env python3
"""ble_bridge.py - BLE Central <-> usb_server._process_msg bridge.

Architecture (role-reversed from v0.3.7):
  Phone (Peripheral) -- Notify --> PC (Central, this bridge) -> usb_server._process_msg
  PC (Central) -- Write --> Phone (Peripheral)

Frame protocol (unchanged):
  [0xAA][total][idx][chunk<=16 bytes]    3-byte header
  total <= 255; max msg = 255*16 = 4080 bytes

Auto pairing (免配对码):
  On first notify from phone, register session to usb_server._usb_sessions.
  Phone does NOT need to send pair / secret.
"""
import asyncio
import json
import logging
import time
from typing import Optional

import ble_server
import usb_server

log = logging.getLogger("phonekb.ble_bridge")

MAGIC = 0xAA
CHUNK_DATA = 16


class _RxAssembler:
    def __init__(self):
        self._total = 0
        self._parts = []
        self._seen = 0
        self._ready = True

    def feed(self, raw: bytes) -> Optional[bytes]:
        if len(raw) < 4 or raw[0] != MAGIC:
            return None
        total = raw[1]
        idx = raw[2]
        chunk = raw[3:]
        if self._ready:
            if total < 1 or idx != 0:
                return None
            self._total = total
            self._parts = [b''] * total
            self._seen = 0
            self._ready = False
        if total != self._total or idx >= total:
            self._ready = True
            return None
        if idx >= len(self._parts) or len(self._parts[idx]) > 0:
            self._ready = True
            return None
        self._parts[idx] = chunk
        self._seen += 1
        if self._seen >= self._total:
            self._ready = True
            return b''.join(self._parts)
        return None


def _frame_encode(payload: bytes) -> list:
    if not payload:
        return []
    if len(payload) <= CHUNK_DATA:
        return [bytes([MAGIC, 1, 0]) + payload]
    total = (len(payload) + CHUNK_DATA - 1) // CHUNK_DATA
    if total > 255:
        log.warning('BLE TX > 255 frames, drop (len=%d)' % len(payload))
        return []
    out = []
    for i in range(total):
        seg = payload[i * CHUNK_DATA : (i + 1) * CHUNK_DATA]
        out.append(bytes([MAGIC, total, i]) + seg)
    return out


class BLESession:
    """Mock ws object so _process_msg / _send work unchanged.

    send() writes to phone's Write characteristic (PC -> phone).
    """
    def __init__(self, handles: dict, addr: str = 'ble:00:00'):
        self.handles = handles
        self.remote_address = ('ble', addr)
        self.closed = False
        self._tx_lock = asyncio.Lock()

    async def send(self, json_str: str):
        if self.closed or self.handles is None:
            return
        payload = json_str.encode('utf-8')
        frames = _frame_encode(payload)
        if not frames:
            return
        async with self._tx_lock:
            for f in frames:
                if self.closed:
                    return
                ok = await ble_server.write_to_phone_async(self.handles, f)
                if not ok:
                    log.warning('BLE write frame failed')
                    self.closed = True
                    return
                await asyncio.sleep(0.02)

    async def close(self):
        self.closed = True


async def run_ble_bridge(loop: Optional[asyncio.AbstractEventLoop] = None):
    if loop is None:
        loop = asyncio.get_running_loop()

    session_ref = {'s': None}
    rx_ref = {'asm': [_RxAssembler()]}

    async def on_msg(raw: bytes):
        if session_ref['s'] is None or session_ref['s'].closed:
            sess = BLESession(handles_box, addr='ble:%05x' % (id(handles_box) & 0xFFFF))
            session_ref['s'] = sess
            rx_ref['asm'][0] = _RxAssembler()
            usb_server._usb_sessions[sess] = {'ip': 'ble-local', 'paired_at': time.time()}
            usb_server._usb_targets.setdefault(sess, 0)
            log.info('BLE new session registered to _usb_sessions')

        if raw and raw[0] == MAGIC:
            full = rx_ref['asm'][0].feed(raw)
            if full is None:
                return
        else:
            full = raw
        try:
            msg = json.loads(full.decode('utf-8'))
        except Exception as e:
            log.warning('BLE JSON parse failed: %s | raw=%s' % (e, full[:64]))
            return
        action = msg.get('action', '?')
        log.info('BLE action=%s msg=%s' % (action, msg if action in ('type', 'shortcut') else '<...>'))
        sess = session_ref['s']
        try:
            await usb_server._process_msg(sess, msg)
        except Exception as e:
            log.exception('BLE _process_msg failed: ' + str(e))

    handles_box: dict = {}
    res = await ble_server.start_ble_central(
        on_message=on_msg,
        name='PhoneKB',
        loop=loop,
    )
    handles_box.update(res)
    log.info('BLE Central bridge ready, scanning for PhoneKB')

    try:
        await asyncio.Future()
    except asyncio.CancelledError:
        log.info('BLE bridge cancelled')
        if session_ref['s']:
            usb_server._unregister_codex_client(session_ref['s'])
            usb_server._usb_sessions.pop(session_ref['s'], None)
            usb_server._usb_targets.pop(session_ref['s'], None)
            await session_ref['s'].close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s', datefmt='%H:%M:%S')
    asyncio.run(run_ble_bridge())

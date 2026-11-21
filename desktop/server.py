"""server.py - 精简版 WebSocket 服务。

Actions 支持: pair / ping / pick_target / type / mouse / simulate_key

前两个 action 不需要配对（pair 用于建立 session，其它都要求 ws in _sessions）。
"""
import asyncio
import ctypes
import json
import logging
import os
import secrets
import hmac
import hashlib
import time
from typing import Optional

import websockets
from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

import keytrigger
import mouse
import custom_keys_loader
import layouts_loader
import gamepad_layouts_loader
import desktop_actions
import codex_bridge
import codex_voice
import timeline_control
from input_recorder import InputRecorder

def _resolve_data_path(name: str) -> str:
    """在 PyInstaller --onefile bundle 与裸 python 都能找到 data 文件。
    优先级：
      1) __file__ 所在目录（dev 模式）
      2) sys.executable 所在目录（--onefile bundle，executable 即 .exe）
      3) sys._MEIPASS 临时目录（--onefile 实际 bundle 内）
    返回值：第一个已存在的路径；都不存在返回第 1 个（让 open() 抛 FileNotFoundError 暴露）。"""
    import sys as _sys
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), name),
        os.path.join(os.path.dirname(os.path.abspath(_sys.executable)), name),
    ]
    meipass = getattr(_sys, "_MEIPASS", None)
    if meipass:
        candidates.append(os.path.join(meipass, name))
    for c in candidates:
        try:
            if os.path.exists(c):
                return c
        except Exception:
            continue
    return candidates[0]



logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("phonekb.server")

user32 = ctypes.WinDLL("user32", use_last_error=True)

# 全局配置（由 main.py 启动时注入）
SECRET_CODE: Optional[str] = None
SECRET_FULL: Optional[str] = None
PORT: int = 9876

# 状态
def load_custom_keys():
    """空实现：兼容 main.py 调用。"""
    pass


_sessions: dict = {}              # ws -> meta
_session_targets: dict = {}      # ws -> 目标窗口 hwnd
_gamepad_held_keys: dict = {}    # ws -> {key name: reference count}
_gamepad_held_mouse: dict = {}   # ws -> {mouse button: reference count}
_server_loop = None
_on_pair_callbacks: list = []
_recorders: dict = {}


def on_pair(callback):
    _on_pair_callbacks.append(callback)


def _fire_on_pair():
    for cb in _on_pair_callbacks:
        try:
            cb()
        except Exception as e:
            log.warning(f"on_pair cb err: {e}")
_session_targets: dict = {}      # ws -> 目标窗口 hwnd


def load_data():
    """空实现：兼容 main.py 调用（V2 数据模型已经删除）。"""
    pass


def configure(code, full, port=9876):
    global SECRET_CODE, SECRET_FULL, PORT
    SECRET_CODE = code
    SECRET_FULL = full
    PORT = port


def _check_secret(s):
    """校验 pair secret: 6 位配对码（手输）或 QR token（HMAC 时间窗）。"""
    if not s:
        return False
    s = str(s)
    # 6 位配对码路径（手输 / 手动粘贴）
    if SECRET_CODE and len(s) == 6 and s.upper() == SECRET_CODE:
        return True
    # QR token 路径：'<ts>.<machex16>'，HMAC(SECRET_FULL, ts) 前 16 hex，±60s
    if SECRET_FULL and "." in s:
        try:
            ts_str, mac = s.split(".", 1)
            ts = int(ts_str)
        except Exception:
            return False
        now = int(time.time())
        if abs(now - ts) > 60:
            return False
        expected = hmac.new(SECRET_FULL.encode("ascii"), str(ts).encode("ascii"), hashlib.sha256).hexdigest()[:16]
        if hmac.compare_digest(mac, expected):
            log.info("QR token 校验成功 ts=%d", ts)
            return True
        return False
    # 兼容 老 32 位 secret 直接发（指数 slash 直接发 secret）
    if SECRET_FULL and s == SECRET_FULL:
        return True
    return False


def _target_for(ws) -> int:
    return _session_targets.get(ws, 0)


async def _send(ws, obj):
    try:
        await ws.send(json.dumps(obj, ensure_ascii=False))
    except ConnectionClosed:
        pass


def _codex_client_key(ws) -> str:
    return "wifi:" + str(id(ws))


def _register_codex_client(ws, loop) -> str:
    client_key = _codex_client_key(ws)

    def sender(event):
        if loop.is_closed():
            raise RuntimeError("Wi-Fi client event loop is closed")
        asyncio.run_coroutine_threadsafe(_send(ws, event), loop)

    codex_bridge.register_client(client_key, sender)
    return client_key

async def _push_layouts(ws):
    try:
        data = layouts_loader.load()
        await _send(ws, {"action": "layouts", "data": data})
    except Exception as e:
        log.exception("_push_layouts fail")


async def _push_gamepad_layouts(ws):
    try:
        await _send(ws, {"action": "gamepad_layouts", "data": gamepad_layouts_loader.load()})
    except Exception:
        log.exception("_push_gamepad_layouts fail")


async def _broadcast_gamepad_layouts():
    for client in list(_sessions):
        await _push_gamepad_layouts(client)


def notify_gamepad_layouts_changed():
    """Allow the loopback desktop editor to notify connected phones after save."""
    if _server_loop and _server_loop.is_running():
        asyncio.run_coroutine_threadsafe(_broadcast_gamepad_layouts(), _server_loop)


def _gamepad_key_names(raw_keys):
    if isinstance(raw_keys, str):
        raw_keys = [raw_keys]
    if not isinstance(raw_keys, list) or not raw_keys or len(raw_keys) > 8:
        return []
    aliases = {"↑": "up", "↓": "down", "←": "left", "→": "right", "control": "ctrl", "escape": "esc", " ": "space"}
    keys = []
    for value in raw_keys:
        key = str(value or "").strip().lower()
        key = aliases.get(key, key)
        if not key or len(key) > 32 or key in keys or not keytrigger._resolve_key(key):
            return []
        keys.append(key)
    return keys


def _set_gamepad_keys(ws, keys, is_down):
    held = _gamepad_held_keys.setdefault(ws, {})
    ok = True
    for key in keys:
        count = int(held.get(key, 0))
        if is_down:
            held[key] = count + 1
            if count == 0:
                ok = bool(keytrigger.key_down(key)) and ok
        elif count > 0:
            if count == 1:
                held.pop(key, None)
                ok = bool(keytrigger.key_up(key)) and ok
            else:
                held[key] = count - 1
    if not held:
        _gamepad_held_keys.pop(ws, None)
    return ok


def _release_gamepad_keys(ws):
    held = _gamepad_held_keys.pop(ws, {})
    for key in held:
        try:
            keytrigger.key_up(key)
        except Exception:
            pass


_MOUSE_BUTTONS = {"left", "right", "middle"}


def _set_held_mouse(ws, button, is_down):
    button = str(button or "left").lower()
    if button not in _MOUSE_BUTTONS:
        return False
    held = _gamepad_held_mouse.setdefault(ws, {})
    count = int(held.get(button, 0))
    if is_down:
        held[button] = count + 1
        if count == 0:
            ok = bool(mouse.down(button))
            if not ok:
                held.pop(button, None)
                if not held:
                    _gamepad_held_mouse.pop(ws, None)
            return ok
        return True
    if count <= 0:
        return True
    if count == 1:
        held.pop(button, None)
        ok = bool(mouse.up(button))
    else:
        held[button] = count - 1
        ok = True
    if not held:
        _gamepad_held_mouse.pop(ws, None)
    return ok


def _release_held_mouse(ws):
    held = _gamepad_held_mouse.pop(ws, {})
    for button in held:
        try:
            mouse.up(button)
        except Exception:
            pass


async def _execute_macro(ws, steps, interval_ms=50):
    """Run a macro while releasing any unmatched down steps on every exit path."""
    loop = asyncio.get_event_loop()
    owned_keys = {}
    owned_mouse = {}
    supported_types = {"key", "mouse", "text", "wait_ms", "enter"}
    macro_steps = [step for step in steps if isinstance(step, dict) and step.get("type") in supported_types]
    try:
        interval_ms = int(interval_ms if interval_ms is not None else 50)
    except (TypeError, ValueError):
        interval_ms = 50
    interval_ms = max(0, min(1000, interval_ms))
    try:
        for index, step in enumerate(macro_steps):
            step_type = step.get("type")
            if step_type == "key":
                raw_keys = list(step.get("modifiers") or [])
                if step.get("key"):
                    raw_keys.append(step.get("key"))
                keys = _gamepad_key_names(raw_keys)
                mode = str(step.get("mode") or "tap")
                if not keys:
                    continue
                if mode == "down":
                    await loop.run_in_executor(None, _set_gamepad_keys, ws, keys, True)
                    for value in keys:
                        owned_keys[value] = int(owned_keys.get(value, 0)) + 1
                elif mode == "up":
                    releasable = [value for value in keys if owned_keys.get(value, 0) > 0]
                    if releasable:
                        await loop.run_in_executor(None, _set_gamepad_keys, ws, list(reversed(releasable)), False)
                    for value in releasable:
                        if owned_keys.get(value, 0) > 1:
                            owned_keys[value] -= 1
                        else:
                            owned_keys.pop(value, None)
                else:
                    await loop.run_in_executor(None, keytrigger.simulate_key, step.get("modifiers", []) or [], step.get("key", ""))
            elif step_type == "mouse":
                op = str(step.get("op") or "click")
                button = str(step.get("button") or "left")
                if op == "wheel":
                    await loop.run_in_executor(None, mouse.wheel, int(step.get("delta", 120) or 120))
                elif op == "down":
                    if await loop.run_in_executor(None, _set_held_mouse, ws, button, True):
                        owned_mouse[button] = int(owned_mouse.get(button, 0)) + 1
                elif op == "up":
                    if owned_mouse.get(button, 0) > 0:
                        await loop.run_in_executor(None, _set_held_mouse, ws, button, False)
                        if owned_mouse.get(button, 0) > 1:
                            owned_mouse[button] -= 1
                        else:
                            owned_mouse.pop(button, None)
                else:
                    await loop.run_in_executor(None, mouse.click, button, int(step.get("count", 1) or 1))
            elif step_type == "text":
                await loop.run_in_executor(None, keytrigger.input_text, step.get("value", ""))
            elif step_type == "wait_ms":
                await asyncio.sleep(max(0, min(60000, int(step.get("value", 0) or 0))) / 1000.0)
            elif step_type == "enter":
                await loop.run_in_executor(None, keytrigger.simulate_key, [], "enter")
            if index < len(macro_steps) - 1 and step_type != "wait_ms" and macro_steps[index + 1].get("type") != "wait_ms" and interval_ms:
                await asyncio.sleep(interval_ms / 1000.0)
    finally:
        for value, count in owned_keys.items():
            for _ in range(count):
                await loop.run_in_executor(None, _set_gamepad_keys, ws, [value], False)
        for button, count in owned_mouse.items():
            for _ in range(count):
                await loop.run_in_executor(None, _set_held_mouse, ws, button, False)


def _shortcut_keys_for_slot_message(message):
    """Resolve one saved shortcut slot into the ordered keys to hold."""
    slot_id = str(message.get("id", ""))
    if not slot_id:
        return [], "missing id"
    try:
        data = layouts_loader.load()
    except Exception as exc:
        return [], "load fail: " + str(exc)
    target = None
    for layout in data.get("layouts") or []:
        for page in layout.get("pages") or []:
            for slot in page.get("slots") or []:
                key = slot.get("key") or {}
                if key.get("id") == slot_id:
                    target = slot
                    break
            if target:
                break
        if target:
            break
    if not target:
        payload_target = message.get("slot")
        if ((payload_target or {}).get("key") or {}).get("type") == "shortcut":
            target = payload_target
    key = (target or {}).get("key") or {}
    if key.get("type") != "shortcut":
        return [], "slot is not a shortcut"
    shortcut = key.get("shortcut") or {}
    raw_keys = list(shortcut.get("modifiers") or [])
    if shortcut.get("key"):
        raw_keys.append(shortcut.get("key"))
    keys = _gamepad_key_names(raw_keys)
    if not keys:
        return [], "invalid shortcut"
    return keys, ""


def _codex_long_action_for_slot_message(message):
    """Resolve one saved Codex key and execute its configured long-press action."""
    slot_id = str(message.get("id", ""))
    if not slot_id:
        return {"action": "codex_bind_current_slot_ack", "ok": False, "msg": "missing id"}
    try:
        data = layouts_loader.load()
    except Exception as exc:
        return {"action": "codex_bind_current_slot_ack", "ok": False, "msg": "load fail: " + str(exc)}
    for layout in data.get("layouts") or []:
        for page in layout.get("pages") or []:
            for slot in page.get("slots") or []:
                key = slot.get("key") or {}
                if key.get("id") == slot_id:
                    if key.get("type") != "codex":
                        return {"action": "codex_bind_current_slot_ack", "ok": False, "msg": "slot is not a Codex key"}
                    return codex_bridge.handle_layout_long_action(key)
    return {"action": "codex_bind_current_slot_ack", "ok": False, "msg": "slot not found"}


def _validate_key_definition(key):
    """Reject unsafe new action definitions before they enter layouts.json."""
    if not isinstance(key, dict):
        return "key must be object"
    key_type = key.get("type")
    if key_type == "mouse":
        mouse_config = key.get("mouse") or {}
        if mouse_config.get("op", "click") not in {"click", "down", "up", "wheel"}:
            return "不支持的鼠标动作"
        if mouse_config.get("op") != "wheel" and mouse_config.get("button", "left") not in _MOUSE_BUTTONS:
            return "不支持的鼠标按键"
    if key_type == "macro":
        macro = key.get("macro") or {}
        steps = macro.get("steps")
        if not isinstance(steps, list) or not steps or len(steps) > 100:
            return "多步操作步骤无效"
        try:
            interval_ms = int(macro.get("interval_ms", 50))
            if interval_ms < 0 or interval_ms > 1000:
                return "统一步骤间隔必须是 0 到 1000 毫秒"
        except Exception:
            return "统一步骤间隔无效"
        for step in steps:
            if not isinstance(step, dict):
                return "多步操作步骤无效"
            step_type = step.get("type")
            if step_type == "key" and step.get("mode", "tap") not in {"tap", "down", "up"}:
                return "不支持的键盘执行方式"
            if step_type == "mouse":
                op = step.get("op", "click")
                if op not in {"click", "down", "up", "wheel"}:
                    return "不支持的鼠标动作"
                if op != "wheel" and step.get("button", "left") not in _MOUSE_BUTTONS:
                    return "不支持的鼠标按键"
            if step_type == "wait_ms":
                try:
                    if int(step.get("value", 0)) < 0 or int(step.get("value", 0)) > 60000:
                        return "等待时间必须是 0 到 60000 毫秒"
                except Exception:
                    return "等待时间无效"
            if step_type not in {"key", "mouse", "text", "wait_ms", "enter"}:
                return "不支持的多步操作类型"
    if key_type == "link":
        _, error = desktop_actions.validate_url((key.get("link") or {}).get("url"))
        return error
    if key_type == "app":
        app_id = (key.get("app") or {}).get("id")
        if not desktop_actions.is_authorized_app(app_id):
            return "该软件尚未授权，请先读取电脑复制的路径"
    if key_type == "codex":
        config = key.get("codex")
        if not isinstance(config, dict):
            return "Codex 按键配置缺失"
        if config.get("action") not in {"focus_task", "approve", "reject"}:
            return "不支持的 Codex 按键动作"
        try:
            slot = int(config.get("slot"))
        except Exception:
            return "Codex 任务槽必须是 1 到 6"
        if slot < 1 or slot > 6:
            return "Codex 任务槽必须是 1 到 6"
        if config.get("long_press_action") not in {None, "", "bind_current_task"}:
            return "不支持的 Codex 长按动作"
    return None




async def handle_client(ws):
    remote = f"{ws.remote_address[0]}:{ws.remote_address[1]}"
    loop = asyncio.get_running_loop()
    codex_client_key = _codex_client_key(ws)
    log.info(f"连接: {remote}")
    try:
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except Exception:
                await _send(ws, {"action": "error", "msg": "invalid json"})
                continue
            action = msg.get("action")

            # ---- 心跳 ----
            if action == "ping":
                session = _sessions.get(ws)
                if session is not None:
                    session["last_pong"] = time.time()
                await _send(ws, {"action": "pong"})
                continue

            # ---- 配对 ----
            if action == "pair":
                secret = str(msg.get("secret", ""))
                if _check_secret(secret):
                    ip = remote.split(":")[0]
                    _sessions[ws] = {
                        "ip": ip,
                        "paired_at": time.time(),
                        "ua": str(msg.get("ua", ""))[:120],
                    }
                    _session_targets.setdefault(ws, 0)
                    _register_codex_client(ws, loop)
                    _fire_on_pair()
                    log.info(f"配对成功: {remote}")
                    await _send(ws, {"action": "paired", "ok": True, "server": "phonekb/1.0", "proto": 1})
                else:
                    log.warning(f"配对失败: {remote}")
                    await _send(ws, {"action": "paired", "ok": False})
                continue

            # 后续 action 都需要先配对
            if ws not in _sessions:
                await _send(ws, {"action": "error", "msg": "not paired"})
                continue

            if action == "record_start":
                recorder = _recorders.get(ws)
                if recorder and recorder.recording:
                    await _send(ws, {"action": "record_started", "ok": False, "msg": "已经在录制"})
                    continue
                recorder = InputRecorder()
                ok, error = recorder.start()
                if ok:
                    _recorders[ws] = recorder
                await _send(ws, {"action": "record_started", "ok": ok, "msg": error})
                continue

            if action == "record_stop":
                recorder = _recorders.pop(ws, None)
                if not recorder:
                    await _send(ws, {"action": "record_stopped", "ok": False, "msg": "当前没有录制"})
                    continue
                macro = recorder.stop()
                await _send(ws, {"action": "record_stopped", "ok": True, "macro": macro})
                continue

            if action == "test_macro":
                macro = msg.get("macro") or {}
                steps = macro.get("steps") or []
                await _execute_macro(ws, steps, macro.get("interval_ms", 50))
                await _send(ws, {"action": "test_macro_ack", "ok": True})
                continue

            if action == "list_devices":
                devices = []
                for index, meta in enumerate(list(_sessions.values())):
                    devices.append({
                        "index": index,
                        "ip": meta.get("ip", ""),
                        "ua": meta.get("ua", ""),
                        "paired_at": int(float(meta.get("paired_at", 0)) * 1000),
                        "last_pong": int(float(meta.get("last_pong", 0)) * 1000),
                    })
                await _send(ws, {"action": "devices", "devices": devices})
                continue

            # ---- Custom gamepad layouts and real-time input ----
            if action == "get_gamepad_layouts":
                await _push_gamepad_layouts(ws)
                continue

            if action == "save_gamepad_layouts":
                payload = msg.get("data")
                if not isinstance(payload, dict):
                    await _send(ws, {"action": "save_gamepad_layouts_ack", "ok": False, "msg": "data must be object"})
                    continue
                try:
                    saved = gamepad_layouts_loader.save(payload)
                    await _send(ws, {"action": "save_gamepad_layouts_ack", "ok": True, "data": saved})
                    await _broadcast_gamepad_layouts()
                except Exception as e:
                    log.exception("save_gamepad_layouts fail")
                    await _send(ws, {"action": "save_gamepad_layouts_ack", "ok": False, "msg": str(e)})
                continue

            if action == "set_active_gamepad_layout":
                try:
                    ok, data = gamepad_layouts_loader.set_active(msg.get("layout_id"))
                    await _send(ws, {"action": "set_active_gamepad_layout_ack", "ok": ok, "data": data})
                    if ok:
                        await _broadcast_gamepad_layouts()
                except Exception as e:
                    await _send(ws, {"action": "set_active_gamepad_layout_ack", "ok": False, "msg": str(e)})
                continue

            if action == "gamepad_key":
                keys = _gamepad_key_names(msg.get("keys"))
                if not keys:
                    await _send(ws, {"action": "gamepad_key_ack", "ok": False, "msg": "invalid key list"})
                    continue
                loop = asyncio.get_event_loop()
                ok = await loop.run_in_executor(None, _set_gamepad_keys, ws, keys, bool(msg.get("down")))
                await _send(ws, {"action": "gamepad_key_ack", "ok": ok, "down": bool(msg.get("down")), "keys": keys})
                continue

            if action == "hold_slot":
                keys, error = _shortcut_keys_for_slot_message(msg)
                if error:
                    await _send(ws, {"action": "hold_slot_ack", "ok": False, "id": str(msg.get("id", "")), "msg": error})
                    continue
                is_down = bool(msg.get("down"))
                ordered_keys = keys if is_down else list(reversed(keys))
                loop = asyncio.get_event_loop()
                ok = await loop.run_in_executor(None, _set_gamepad_keys, ws, ordered_keys, is_down)
                await _send(ws, {"action": "hold_slot_ack", "ok": ok, "id": str(msg.get("id", "")), "down": is_down})
                continue

            if action == "hold_mouse":
                button = str(msg.get("button", "left"))
                loop = asyncio.get_event_loop()
                ok = await loop.run_in_executor(None, _set_held_mouse, ws, button, bool(msg.get("down")))
                await _send(ws, {"action": "hold_mouse_ack", "ok": ok, "id": str(msg.get("id", "")), "down": bool(msg.get("down"))})
                continue

            if action == "gamepad_mouse_move":
                try:
                    dx = max(-500, min(500, int(msg.get("dx", 0))))
                    dy = max(-500, min(500, int(msg.get("dy", 0))))
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, mouse.move, dx, dy)
                    await _send(ws, {"action": "gamepad_mouse_move_ack", "ok": True})
                except Exception as e:
                    await _send(ws, {"action": "gamepad_mouse_move_ack", "ok": False, "msg": str(e)})
                continue

            if action == "codex_zhipu_start":
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, codex_voice.start_zhipu_dictation)
                if result.get("ok") and result.get("hwnd"):
                    _session_targets[ws] = int(result["hwnd"])
                await _send(ws, dict({"action": "codex_zhipu_start_ack"}, **result))
                continue

            if action == "codex_zhipu_stop":
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, codex_voice.stop_zhipu_dictation)
                await _send(ws, dict({"action": "codex_zhipu_stop_ack"}, **result))
                continue

            if action == "codex_submit_enter":
                loop = asyncio.get_event_loop()
                hwnd = _target_for(ws)
                result = await loop.run_in_executor(None, codex_voice.submit_codex_composer, hwnd)
                await _send(ws, dict({"action": "codex_submit_enter_ack"}, **result))
                continue

            if action == "codex_test_input":
                request_id = str(msg.get("request_id") or "")
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, codex_voice.enter_test_phrase)
                await _send(ws, dict({
                    "action": "codex_test_input_ack",
                    "request_id": request_id,
                }, **result))
                continue

            if action == "codex_voice_start":
                target = codex_voice.capture_current_target()
                if target.get("ok"):
                    _session_targets[ws] = target["hwnd"]
                await _send(ws, dict({"action": "codex_voice_start_ack"}, **target))
                continue

            if action == "codex_dictate":
                text = str(msg.get("text") or "")
                append_space = bool(msg.get("append_space"))
                hwnd = _target_for(ws)
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, codex_voice.type_into_target, hwnd, text, append_space)
                await _send(ws, dict({"action": "codex_dictate_ack"}, **result))
                continue

            if isinstance(action, str) and action.startswith("codex_"):
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, codex_bridge.handle_message, msg)
                await _send(ws, result)
                continue

            # ---- Read and authorize one copied executable path ----
            if action == "read_desktop_clipboard":
                loop = asyncio.get_event_loop()
                app, error = await loop.run_in_executor(None, desktop_actions.authorize_clipboard_app)
                if error:
                    await _send(ws, {"action": "clipboard_app", "ok": False, "msg": error})
                else:
                    await _send(ws, {"action": "clipboard_app", "ok": True, "app": app})
                continue

            if action == "read_desktop_clipboard_url":
                loop = asyncio.get_event_loop()
                url, error = await loop.run_in_executor(None, desktop_actions.read_clipboard_url)
                await _send(ws, {"action": "clipboard_url", "ok": not error, "url": url or "", "msg": error or ""})
                continue

            # ---- 选目标窗口（3 秒倒计时） ----
            if action == "pick_target":
                await _send(ws, {"action": "pick_started"})
                async def do_pick():
                    try:
                        await asyncio.sleep(3)
                        hwnd = user32.GetForegroundWindow()
                        length = user32.GetWindowTextLengthW(hwnd)
                        buff = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buff, length + 1)
                        title = buff.value or "(无标题)"
                        _session_targets[ws] = hwnd
                        log.info(f"pick_target: [{hwnd}] {title}")
                        await _send(ws, {"action": "target_changed", "hwnd": hwnd, "title": title})
                    except Exception as e:
                        log.exception(f"do_pick: {e}")
                asyncio.ensure_future(do_pick())
                continue

            # ---- 文字输入 ----
            if action == "type":
                text = str(msg.get("text", ""))
                if len(text) > 5000:
                    await _send(ws, {"action": "error", "msg": "text too long"})
                    continue
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, keytrigger.input_text, text)
                await _send(ws, {"action": "type_done", "text": text, **result})
                continue

            # ---- 模拟键（核心：modifier + key） ----
            if action == "simulate_key":
                modifiers = msg.get("modifiers", []) or []
                key = msg.get("key", "")
                loop = asyncio.get_event_loop()
                ok = await loop.run_in_executor(None, keytrigger.simulate_key, modifiers, key)
                log.info(f"simulate_key: mods={modifiers} key={key!r} ok={ok}")
                await _send(ws, {"action": "simulate_key_ack", "modifiers": modifiers, "key": key, "ok": ok})
                continue

            # ---- 鼠标控制 ----
            if action == "mouse":
                op = str(msg.get("op", ""))
                loop = asyncio.get_event_loop()
                try:
                    if op == "move":
                        # Relative motion is a tiny SendInput call. Avoid a
                        # thread-pool hop and an ACK for every touch frame.
                        mouse.move(int(msg.get("dx", 0)), int(msg.get("dy", 0)))
                        continue
                    elif op == "move_abs":
                        await loop.run_in_executor(None, mouse.move_abs, int(msg.get("x", 0)), int(msg.get("y", 0)))
                    elif op == "click":
                        await loop.run_in_executor(None, mouse.click, str(msg.get("button", "left")), int(msg.get("count", 1)))
                    elif op == "down":
                        await loop.run_in_executor(None, mouse.down, str(msg.get("button", "left")))
                    elif op == "up":
                        await loop.run_in_executor(None, mouse.up, str(msg.get("button", "left")))
                    elif op == "wheel":
                        await loop.run_in_executor(None, mouse.wheel, int(msg.get("delta", 0)))
                    elif op == "hwheel":
                        await loop.run_in_executor(None, mouse.hwheel, int(msg.get("delta", 0)))
                    elif op == "zoom":
                        await loop.run_in_executor(None, mouse.zoom, int(msg.get("delta", 0)))
                    elif op == "position":
                        x, y = mouse.position()
                        await _send(ws, {"action": "mouse_position", "x": x, "y": y})
                        continue
                    else:
                        await _send(ws, {"action": "error", "msg": f"unknown mouse op: {op!r}"})
                        continue
                    await _send(ws, {"action": "mouse_ack", "op": op})
                except Exception as e:
                    log.exception(f"mouse error: {e}")
                    await _send(ws, {"action": "error", "msg": f"mouse failed: {e}"})
                continue

            if action == "timeline_control":
                loop = asyncio.get_event_loop()
                ok, error = await loop.run_in_executor(
                    None,
                    timeline_control.execute,
                    str(msg.get("op", "")),
                    msg.get("delta", 0),
                    _get_target(ws),
                )
                if not ok:
                    await _send(ws, {"action": "timeline_control_error", "msg": error})
                continue

            # ---- trigger named shortcut (panel builtin buttons) ----
            if action == "shortcut":
                name = str(msg.get("name", ""))
                if not name:
                    await _send(ws, {"action": "shortcut_ack", "ok": False, "msg": "missing name"})
                    continue
                try:
                    ck_path = _resolve_data_path("custom_keys.json")
                    with open(ck_path, "r", encoding="utf-8") as _f:
                        _ck = json.loads(_f.read())
                    spec = None
                    for _k in (_ck.get("keys") or []):
                        if _k.get("id") == name or _k.get("label") == name:
                            spec = _k
                            break
                    if not spec:
                        await _send(ws, {"action": "shortcut_ack", "ok": False, "name": name, "msg": "unknown shortcut"})
                        continue
                    mods = spec.get("modifiers", []) or []
                    k = str(spec.get("key", ""))
                    loop = asyncio.get_event_loop()
                    ok = await loop.run_in_executor(None, keytrigger.simulate_key, mods, k)
                    log.info("shortcut: name=" + name + " mods=" + str(mods) + " key=" + k + " ok=" + str(ok))
                    await _send(ws, {"action": "shortcut_ack", "ok": ok, "name": name})
                except Exception as e:
                    log.exception("shortcut error")
                    await _send(ws, {"action": "shortcut_ack", "ok": False, "name": name, "msg": str(e)})
                continue

            # ---- 触发按键槽位（小程序点面板按钮时调用）----
            if action == "trigger_slot_long":
                result = await loop.run_in_executor(None, _codex_long_action_for_slot_message, msg)
                await _send(ws, result)
                continue

            if action == "trigger_slot":
                slot_id = str(msg.get("id", ""))
                if not slot_id:
                    await _send(ws, {"action": "trigger_ack", "ok": False, "msg": "missing id"})
                    continue
                try:
                    data = layouts_loader.load()
                except Exception as e:
                    log.exception("trigger_slot load layouts fail")
                    await _send(ws, {"action": "trigger_ack", "ok": False, "id": slot_id, "msg": f"load fail: {e}"})
                    continue
                # Saved layouts are the source of truth. Payload fallback remains for old clients,
                # but never for actions that can launch a browser or an application.
                target = None
                for _lay in (data.get("layouts") or []):
                    for _page in (_lay.get("pages") or []):
                        for _slot in (_page.get("slots") or []):
                            _k = _slot.get("key")
                            if _k and _k.get("id") == slot_id:
                                target = _slot
                                break
                        if target: break
                    if target: break
                if not target:
                    payload_target = msg.get("slot") or (msg.get("id") if isinstance(msg.get("id"), dict) else None)
                    payload_type = ((payload_target or {}).get("key") or {}).get("type")
                    if payload_type in {"link", "app", "codex"}:
                        await _send(ws, {"action": "trigger_ack", "ok": False, "id": slot_id, "msg": "请先保存此按键后再使用"})
                        continue
                    target = payload_target
                if not target:
                    await _send(ws, {"action": "trigger_ack", "ok": False, "id": slot_id, "msg": "slot not found"})
                    continue
                key = target.get("key", {}) or {}
                key_type = key.get("type", "shortcut")
                loop = asyncio.get_event_loop()
                try:
                    if key_type == "shortcut":
                        sc = key.get("shortcut", {}) or {}
                        mods = sc.get("modifiers", []) or []
                        k = sc.get("key", "")
                        log.info(f"trigger_slot shortcut: {mods}+{k}")
                        await loop.run_in_executor(None, keytrigger.simulate_key, mods, k)
                        await _send(ws, {"action": "trigger_ack", "ok": True, "id": slot_id, "type": "shortcut"})
                    elif key_type == "text":
                        text = (key.get("text", {}) or {}).get("value", "")
                        log.info(f"trigger_slot text: {text!r}")
                        result = await loop.run_in_executor(None, keytrigger.input_text, text)
                        await _send(ws, {"action": "trigger_ack", "id": slot_id, "type": "text", **result})
                    elif key_type == "macro":
                        macro = key.get("macro", {}) or {}
                        steps = macro.get("steps", []) or []
                        log.info(f"trigger_slot macro: {len(steps)} steps")
                        await _execute_macro(ws, steps, macro.get("interval_ms", 50))
                        await _send(ws, {"action": "trigger_ack", "ok": True, "id": slot_id, "type": "macro"})
                    elif key_type == "mouse":
                        mo = key.get("mouse", {}) or {}
                        m_op = str(mo.get("op", "click"))
                        if m_op == "click":
                            await loop.run_in_executor(None, mouse.click, str(mo.get("button", "left")), int(mo.get("count", 1)))
                        elif m_op == "wheel":
                            await loop.run_in_executor(None, mouse.wheel, int(mo.get("delta", 120)))
                        elif m_op == "down":
                            await loop.run_in_executor(None, mouse.down, str(mo.get("button", "left")))
                        elif m_op == "up":
                            await loop.run_in_executor(None, mouse.up, str(mo.get("button", "left")))
                        else:
                            raise Exception("unknown mouse op: " + m_op)
                        log.info(f"trigger_slot mouse: {m_op}")
                        await _send(ws, {"action": "trigger_ack", "ok": True, "id": slot_id, "type": "mouse"})
                    elif key_type == "link":
                        url = (key.get("link", {}) or {}).get("url")
                        ok, reason = await loop.run_in_executor(None, desktop_actions.open_url, url)
                        await _send(ws, {"action": "trigger_ack", "ok": ok, "id": slot_id, "type": "link", "msg": reason})
                    elif key_type == "app":
                        app_id = (key.get("app", {}) or {}).get("id")
                        ok, reason = await loop.run_in_executor(None, desktop_actions.launch_authorized_app, app_id)
                        await _send(ws, {"action": "trigger_ack", "ok": ok, "id": slot_id, "type": "app", "msg": reason})
                    elif key_type == "codex":
                        result = await loop.run_in_executor(None, codex_bridge.handle_layout_action, key)
                        await _send(ws, {
                            "action": "trigger_ack",
                            "ok": bool(result.get("ok")),
                            "id": slot_id,
                            "type": "codex",
                            "msg": result.get("msg", ""),
                            "codex_action": result.get("layout_action", ""),
                            "slot": result.get("slot"),
                        })
                    else:
                        await _send(ws, {"action": "trigger_ack", "ok": False, "id": slot_id, "msg": f"unknown type: {key_type}"})
                except Exception as e:
                    log.exception(f"trigger_slot exec fail")
                    await _send(ws, {"action": "trigger_ack", "ok": False, "id": slot_id, "msg": f"{type(e).__name__}: {e}"})
                continue


            # ---- 切换激活布局（面板页切换模板）----
            if action == "set_active":
                layout_id = str(msg.get("layout_id", ""))
                page_id = msg.get("page_id")
                if not layout_id:
                    await _send(ws, {"action": "set_active_ack", "ok": False, "msg": "missing layout_id"})
                    continue
                try:
                    page_id_str = str(page_id) if page_id else None
                    ok = layouts_loader.set_active(layout_id, page_id_str)
                    log.info(f"set_active: layout={layout_id} page={page_id_str} ok={ok}")
                    await _send(ws, {"action": "set_active_ack", "ok": ok, "layout_id": layout_id, "page_id": page_id_str})
                except Exception as e:
                    log.exception("set_active fail")
                    await _send(ws, {"action": "set_active_ack", "ok": False, "layout_id": layout_id, "msg": str(e)})
                continue

            # ---- layouts 推送辅助 ----
            # ---- 新建槽位（点空格子 + 编辑键保存）----
            if action == "add_slot":
                layout_id = str(msg.get("layout_id", ""))
                page_id = str(msg.get("page_id", ""))
                slot = msg.get("slot") or {}
                if not layout_id or not page_id or not isinstance(slot, dict) or not slot.get("key"):
                    await _send(ws, {"action": "add_slot_ack", "ok": False, "msg": "missing params"})
                    continue
                validation_error = _validate_key_definition(slot.get("key"))
                if validation_error:
                    await _send(ws, {"action": "add_slot_ack", "ok": False, "msg": validation_error})
                    continue
                try:
                    new_slot = layouts_loader.add_slot(layout_id, page_id, slot)
                    if not new_slot:
                        await _send(ws, {"action": "add_slot_ack", "ok": False, "msg": "page not found"})
                        continue
                    log.info(f"add_slot: {layout_id}/{page_id} ({new_slot.get('r')},{new_slot.get('c')}) key={new_slot.get('key', {}).get('id')}")
                    await _send(ws, {"action": "add_slot_ack", "ok": True, "r": new_slot.get('r'), "c": new_slot.get('c'), "key_id": new_slot.get('key', {}).get('id')})
                    await _push_layouts(ws)
                except Exception as e:
                    log.exception("add_slot fail")
                    await _send(ws, {"action": "add_slot_ack", "ok": False, "msg": str(e)})
                continue

            # ---- 刷新布局（客户端触发）----
            if action == "reload_layouts":
                await _push_layouts(ws)
                continue

            # ---- 更新槽位（编辑页保存）----
            if action == "update_slot":
                layout_id = str(msg.get("layout_id", ""))
                page_id = str(msg.get("page_id", ""))
                slot_r = int(msg.get("r", -1))
                slot_c = int(msg.get("c", -1))
                updates = msg.get("updates") or {}
                if not layout_id or not page_id or slot_r < 0 or slot_c < 0:
                    await _send(ws, {"action": "update_slot_ack", "ok": False, "msg": "missing params"})
                    continue
                if "key" in updates:
                    validation_error = _validate_key_definition(updates.get("key"))
                    if validation_error:
                        await _send(ws, {"action": "update_slot_ack", "ok": False, "msg": validation_error})
                        continue
                try:
                    ok = layouts_loader.update_slot(layout_id, page_id, slot_r, slot_c, updates)
                    log.info(f"update_slot: {layout_id}/{page_id} ({slot_r},{slot_c}) ok={ok}")
                    await _send(ws, {"action": "update_slot_ack", "ok": ok})
                    await _push_layouts(ws)
                except Exception as e:
                    log.exception("update_slot fail")
                    await _send(ws, {"action": "update_slot_ack", "ok": False, "msg": str(e)})
                continue

            # ---- 删除槽位 ----
            if action == "delete_slot":
                layout_id = str(msg.get("layout_id", ""))
                page_id = str(msg.get("page_id", ""))
                slot_r = int(msg.get("r", -1))
                slot_c = int(msg.get("c", -1))
                if not layout_id or not page_id or slot_r < 0 or slot_c < 0:
                    await _send(ws, {"action": "delete_slot_ack", "ok": False, "msg": "missing params"})
                    continue
                try:
                    ok = layouts_loader.delete_slot(layout_id, page_id, slot_r, slot_c)
                    log.info(f"delete_slot: {layout_id}/{page_id} ({slot_r},{slot_c}) ok={ok}")
                    await _send(ws, {"action": "delete_slot_ack", "ok": ok})
                    await _push_layouts(ws)
                except Exception as e:
                    log.exception("delete_slot fail")
                    await _send(ws, {"action": "delete_slot_ack", "ok": False, "msg": str(e)})
                continue

            # ---- 安装预设 ----
            if action == "install_preset":
                preset_id = str(msg.get("preset_id", ""))
                if not preset_id:
                    await _send(ws, {"action": "install_preset_ack", "ok": False, "msg": "missing preset_id"})
                    continue
                preset_path = os.path.join(layouts_loader.PRESETS_DIR, preset_id + ".json")
                if not os.path.isfile(preset_path):
                    await _send(ws, {"action": "install_preset_ack", "ok": False, "msg": "preset not found: " + preset_id})
                    continue
                try:
                    with open(preset_path, "r", encoding="utf-8") as pf:
                        preset = json.load(pf)
                    new_layout = layouts_loader.install_preset(preset)
                    log.info(f"install_preset: {preset_id} -> {new_layout.get('id')}")
                    await _send(ws, {"action": "install_preset_ack", "ok": True, "id": new_layout.get("id")})
                    await _push_layouts(ws)
                except Exception as e:
                    log.exception("install_preset fail")
                    await _send(ws, {"action": "install_preset_ack", "ok": False, "msg": str(e)})
                continue

            # ---- 改网格行列数 ----
            if action == "set_grid_rows":
                try:
                    rows = int(msg.get("rows", 4))
                    ok = layouts_loader.update_layout_field("__global__", "grid_rows", rows)
                    await _send(ws, {"action": "set_grid_rows_ack", "ok": ok})
                    if ok: await _push_layouts(ws)
                except Exception as e:
                    await _send(ws, {"action": "set_grid_rows_ack", "ok": False, "msg": str(e)})
                continue

            if action == "set_grid_cols":
                try:
                    cols = int(msg.get("cols", 4))
                    ok = layouts_loader.update_layout_field("__global__", "grid_cols", cols)
                    await _send(ws, {"action": "set_grid_cols_ack", "ok": ok})
                    if ok: await _push_layouts(ws)
                except Exception as e:
                    await _send(ws, {"action": "set_grid_cols_ack", "ok": False, "msg": str(e)})
                continue

            # ---- 新建模板 ----
            if action == "add_layout":
                layout_id = str(msg.get("id") or layouts_loader._gen_id(msg.get("name", "layout")))
                page_id = str(msg.get("page_id") or layouts_loader._gen_id("page"))
                try:
                    new_layout = layouts_loader.add_layout({"id": layout_id, "name": msg.get("name", "新方案"), "icon": msg.get("icon", ""), "pages": [{"id": page_id, "name": "页面 1", "icon": "📄", "slots": []}]})
                    if not new_layout:
                        await _send(ws, {"action": "add_layout_ack", "ok": False, "msg": "layout already exists"})
                        continue
                    await _send(ws, {"action": "add_layout_ack", "ok": True, "id": layout_id})
                    await _push_layouts(ws)
                except Exception as e:
                    log.exception("add_layout fail")
                    await _send(ws, {"action": "add_layout_ack", "ok": False, "msg": str(e)})
                continue

            # ---- 删除模板 ----
            if action == "delete_layout":
                layout_id = str(msg.get("layout_id", ""))
                if not layout_id:
                    await _send(ws, {"action": "delete_layout_ack", "ok": False, "msg": "missing layout_id"})
                    continue
                try:
                    ok = layouts_loader.delete_layout(layout_id)
                    await _send(ws, {"action": "delete_layout_ack", "ok": ok})
                    if ok: await _push_layouts(ws)
                except Exception as e:
                    log.exception("delete_layout fail")
                    await _send(ws, {"action": "delete_layout_ack", "ok": False, "msg": str(e)})
                continue

            if action in {"archive_layout", "restore_layout"}:
                layout_id = str(msg.get("layout_id", ""))
                operation = layouts_loader.archive_layout if action == "archive_layout" else layouts_loader.restore_layout
                try:
                    ok = bool(layout_id and operation(layout_id))
                    await _send(ws, {"action": action + "_ack", "ok": ok, "layout_id": layout_id})
                    if ok: await _push_layouts(ws)
                except Exception as e:
                    log.exception(action + " fail")
                    await _send(ws, {"action": action + "_ack", "ok": False, "msg": str(e)})
                continue

            # ---- 重命名模板 ----
            if action == "rename_layout":
                layout_id = str(msg.get("layout_id", ""))
                name = str(msg.get("name", ""))
                icon = msg.get("icon")
                if not layout_id or not name:
                    await _send(ws, {"action": "rename_layout_ack", "ok": False, "msg": "missing params"})
                    continue
                try:
                    ok = layouts_loader.update_layout_field(layout_id, "name", name)
                    if ok and icon:
                        ok = layouts_loader.update_layout_field(layout_id, "icon", icon)
                    await _send(ws, {"action": "rename_layout_ack", "ok": ok})
                    if ok: await _push_layouts(ws)
                except Exception as e:
                    await _send(ws, {"action": "rename_layout_ack", "ok": False, "msg": str(e)})
                continue

            # ---- 新建页 ----
            if action == "add_page":
                layout_id = str(msg.get("layout_id", ""))
                if not layout_id:
                    await _send(ws, {"action": "add_page_ack", "ok": False, "msg": "missing layout_id"})
                    continue
                try:
                    new_page = layouts_loader.add_page(layout_id, {"name": msg.get("name", "新页"), "icon": msg.get("icon", "📄"), "slots": []})
                    await _send(ws, {"action": "add_page_ack", "ok": True, "id": new_page.get("id") if new_page else None})
                    await _push_layouts(ws)
                except Exception as e:
                    await _send(ws, {"action": "add_page_ack", "ok": False, "msg": str(e)})
                continue

            # ---- 删除页 ----
            if action == "delete_page":
                layout_id = str(msg.get("layout_id", ""))
                page_id = str(msg.get("page_id", ""))
                if not layout_id or not page_id:
                    await _send(ws, {"action": "delete_page_ack", "ok": False, "msg": "missing params"})
                    continue
                try:
                    ok = layouts_loader.delete_page(layout_id, page_id)
                    await _send(ws, {"action": "delete_page_ack", "ok": ok})
                    if ok: await _push_layouts(ws)
                except Exception as e:
                    await _send(ws, {"action": "delete_page_ack", "ok": False, "msg": str(e)})
                continue

            # ---- 重命名页 ----
            if action == "rename_page":
                layout_id = str(msg.get("layout_id", ""))
                page_id = str(msg.get("page_id", ""))
                name = str(msg.get("name", ""))
                icon = msg.get("icon")
                if not layout_id or not page_id or not name:
                    await _send(ws, {"action": "rename_page_ack", "ok": False, "msg": "missing params"})
                    continue
                try:
                    ok = layouts_loader.rename_page(layout_id, page_id, name, icon)
                    await _send(ws, {"action": "rename_page_ack", "ok": ok})
                    if ok: await _push_layouts(ws)
                except Exception as e:
                    await _send(ws, {"action": "rename_page_ack", "ok": False, "msg": str(e)})
                continue

            # ---- 自定义快捷键库 ----
            if action == "list_custom_keys":
                try:
                    keys = custom_keys_loader.load()
                    await _send(ws, {"action": "custom_keys", "keys": keys})
                except Exception as e:
                    await _send(ws, {"action": "custom_keys", "keys": [], "error": str(e)})
                continue

            if action == "add_custom_key":
                spec = msg.get("spec", {})
                if not isinstance(spec, dict):
                    await _send(ws, {"action": "add_custom_key_ack", "ok": False, "msg": "spec must be object"})
                    continue
                try:
                    new = custom_keys_loader.add(spec)
                    await _send(ws, {"action": "add_custom_key_ack", "ok": True, "id": new.get("id")})
                except Exception as e:
                    await _send(ws, {"action": "add_custom_key_ack", "ok": False, "msg": str(e)})
                continue

            if action == "delete_custom_key":
                cid = str(msg.get("id", ""))
                if not cid:
                    await _send(ws, {"action": "delete_custom_key_ack", "ok": False, "msg": "missing id"})
                    continue
                try:
                    ok = custom_keys_loader.delete(cid)
                    await _send(ws, {"action": "delete_custom_key_ack", "ok": ok})
                except Exception as e:
                    await _send(ws, {"action": "delete_custom_key_ack", "ok": False, "msg": str(e)})
                continue

            # ---- 未知 action ----
            await _send(ws, {"action": "error", "msg": f"unknown action: {action!r}"})

    except ConnectionClosed:
        pass
    except Exception as e:
        log.exception(f"handle_client 异常: {e}")
    finally:
        recorder = _recorders.pop(ws, None)
        if recorder:
            try: recorder.stop()
            except Exception: pass
        _release_gamepad_keys(ws)
        _release_held_mouse(ws)
        keytrigger.key_up("rctrl")
        codex_bridge.unregister_client(codex_client_key)
        _sessions.pop(ws, None)
        _session_targets.pop(ws, None)
        log.info(f"断开: {remote}")


async def run():
    global _server_loop
    _server_loop = asyncio.get_running_loop()
    log.info(f"WebSocket 监听 0.0.0.0:{PORT}")
    async with serve(handle_client, "0.0.0.0", PORT, max_size=64 * 1024):
        await asyncio.Future()


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 4:
        # main.py 以子进程启动: python server.py CODE SECRET PORT
        SECRET_CODE = sys.argv[1]
        SECRET_FULL = sys.argv[2]
        PORT = int(sys.argv[3])
        asyncio.run(run())
    else:
        # 独立调试
        import pairing
        info = pairing.create_pairing()
        configure(info["code"], info["secret"], info["port"])
        print(f"配对码: {info['code']}  IP: {info['lan_ip']}:{info['port']}")
        asyncio.run(run())

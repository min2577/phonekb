"""usb_server.py - USB 模式的 WebSocket 服务（脱离
 WiFi 使用）。

端口：9877（不和现有 9876 WebSocket 冲突）。
链路：手机 App -> adb reverse tcp:9877 tcp:9877 -> 本服务。
协议：与 server.py（WebSocket 9876）完全相同，业务逻辑 0 修改。
复用：server.py 的 SECRET 全局（import server），保证配对码一致。
复用：keytrigger / mouse / layouts_loader（业务逻辑零修改）。
"""

import asyncio
import os
import ctypes
import json
import logging
import sys
import time

from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

import server  # 复用 SECRET_CODE / SECRET_FULL / on_pair 回调
import keytrigger
import mouse
import custom_keys_loader
import layouts_loader
import desktop_actions
import codex_bridge
import codex_voice
import timeline_control

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("phonekb.usb")

user32 = ctypes.WinDLL("user32", use_last_error=True)

PORT = 9877

_usb_sessions = {}    # ws -> {ip, paired_at}
_usb_targets = {}     # ws -> hwnd
_on_pair_callbacks = []


def on_pair(callback):
    _on_pair_callbacks.append(callback)


def _fire_on_pair():
    for cb in _on_pair_callbacks:
        try:
            cb()
        except Exception as e:
            log.warning("usb on_pair cb err: " + str(e))


def _check_secret(s):
    code = server.SECRET_CODE
    if not code or not s:
        return False
    return s[:6].upper() == code


async def _send(ws, obj):
    try:
        await ws.send(json.dumps(obj, ensure_ascii=False))
    except ConnectionClosed:
        pass


def _codex_client_key(ws) -> str:
    return "usb:" + str(id(ws))


def _register_codex_client(ws) -> str:
    client_key = _codex_client_key(ws)
    loop = asyncio.get_running_loop()

    def sender(event):
        if loop.is_running() and not loop.is_closed():
            asyncio.run_coroutine_threadsafe(_send(ws, event), loop)
            return
        asyncio.run(_send(ws, event))

    codex_bridge.register_client(client_key, sender)
    return client_key


def _unregister_codex_client(ws) -> None:
    codex_bridge.unregister_client(_codex_client_key(ws))

async def _push_layouts(ws):
    try:
        data = layouts_loader.load()
        await _send(ws, {"action": "layouts", "data": data})
    except Exception as e:
        log.exception("_push_layouts fail")


def _validate_key_definition(key):
    if not isinstance(key, dict):
        return "key must be object"
    key_type = key.get("type")
    if key_type == "mouse":
        mouse_config = key.get("mouse") or {}
        if mouse_config.get("op", "click") not in {"click", "down", "up", "wheel"}:
            return "不支持的鼠标动作"
        if mouse_config.get("op") != "wheel" and mouse_config.get("button", "left") not in server._MOUSE_BUTTONS:
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
                if op != "wheel" and step.get("button", "left") not in server._MOUSE_BUTTONS:
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



async def _process_msg(ws, msg):
    action = msg.get("action")

    if action == "ping":
        await _send(ws, {"action": "pong"})
        return

    if action == "pair":
        secret = str(msg.get("secret", ""))
        try:
            ip = ws.remote_address[0]
        except Exception:
            ip = "?"
        # localhost (走 adb reverse) 直接放行：物理接入本身就是信任边界
        is_local = isinstance(ip, str) and ip.startswith("127.")
        if _check_secret(secret) or is_local:
            _usb_sessions[ws] = {"ip": ip, "paired_at": time.time()}
            _usb_targets.setdefault(ws, 0)
            _register_codex_client(ws)
            _fire_on_pair()
            mode = "本地信任" if is_local else "配对码"
            log.info("USB 配对成功 (" + mode + "): " + str(ip))
            await _send(ws, {"action": "paired", "ok": True, "server": "phonekb/1.0"})
        else:
            log.warning("USB 配对失败: " + str(ip))
            await _send(ws, {"action": "paired", "ok": False})
        return

    if ws not in _usb_sessions:
        await _send(ws, {"action": "error", "msg": "not paired"})
        return

    if action == "record_start":
        recorder = server._recorders.get(ws)
        if recorder and recorder.recording:
            await _send(ws, {"action": "record_started", "ok": False, "msg": "已经在录制"})
            return
        recorder = server.InputRecorder()
        ok, error = recorder.start()
        if ok:
            server._recorders[ws] = recorder
        await _send(ws, {"action": "record_started", "ok": ok, "msg": error})
        return

    if action == "record_stop":
        recorder = server._recorders.pop(ws, None)
        if not recorder:
            await _send(ws, {"action": "record_stopped", "ok": False, "msg": "当前没有录制"})
            return
        macro = recorder.stop()
        await _send(ws, {"action": "record_stopped", "ok": True, "macro": macro})
        return

    if action == "test_macro":
        macro = msg.get("macro") or {}
        await server._execute_macro(ws, macro.get("steps") or [], macro.get("interval_ms", 50))
        await _send(ws, {"action": "test_macro_ack", "ok": True})
        return

    if action == "hold_slot":
        keys, error = server._shortcut_keys_for_slot_message(msg)
        if error:
            await _send(ws, {"action": "hold_slot_ack", "ok": False, "id": str(msg.get("id", "")), "msg": error})
            return
        is_down = bool(msg.get("down"))
        ordered_keys = keys if is_down else list(reversed(keys))
        loop = asyncio.get_event_loop()
        ok = await loop.run_in_executor(None, server._set_gamepad_keys, ws, ordered_keys, is_down)
        await _send(ws, {"action": "hold_slot_ack", "ok": ok, "id": str(msg.get("id", "")), "down": is_down})
        return

    if action == "hold_mouse":
        button = str(msg.get("button", "left"))
        loop = asyncio.get_event_loop()
        ok = await loop.run_in_executor(None, server._set_held_mouse, ws, button, bool(msg.get("down")))
        await _send(ws, {"action": "hold_mouse_ack", "ok": ok, "id": str(msg.get("id", "")), "down": bool(msg.get("down"))})
        return

    if action == "trigger_slot_long":
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, server._codex_long_action_for_slot_message, msg)
        await _send(ws, result)
        return

    if action == "codex_zhipu_start":
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, codex_voice.start_zhipu_dictation)
        if result.get("ok") and result.get("hwnd"):
            _usb_targets[ws] = int(result["hwnd"])
        await _send(ws, dict({"action": "codex_zhipu_start_ack"}, **result))
        return

    if action == "codex_zhipu_stop":
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, codex_voice.stop_zhipu_dictation)
        await _send(ws, dict({"action": "codex_zhipu_stop_ack"}, **result))
        return

    if action == "codex_submit_enter":
        loop = asyncio.get_event_loop()
        hwnd = _usb_targets.get(ws, 0)
        result = await loop.run_in_executor(None, codex_voice.submit_codex_composer, hwnd)
        await _send(ws, dict({"action": "codex_submit_enter_ack"}, **result))
        return

    if action == "codex_test_input":
        request_id = str(msg.get("request_id") or "")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, codex_voice.enter_test_phrase)
        await _send(ws, dict({
            "action": "codex_test_input_ack",
            "request_id": request_id,
        }, **result))
        return

    if action == "codex_voice_start":
        target = codex_voice.capture_current_target()
        if target.get("ok"):
            _usb_targets[ws] = target["hwnd"]
        await _send(ws, dict({"action": "codex_voice_start_ack"}, **target))
        return

    if action == "codex_dictate":
        text = str(msg.get("text") or "")
        append_space = bool(msg.get("append_space"))
        hwnd = _usb_targets.get(ws, 0)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, codex_voice.type_into_target, hwnd, text, append_space)
        await _send(ws, dict({"action": "codex_dictate_ack"}, **result))
        return

    if isinstance(action, str) and action.startswith("codex_"):
        _register_codex_client(ws)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, codex_bridge.handle_message, msg)
        await _send(ws, result)
        return

    if action == "read_desktop_clipboard":
        loop = asyncio.get_event_loop()
        app, error = await loop.run_in_executor(None, desktop_actions.authorize_clipboard_app)
        if error:
            await _send(ws, {"action": "clipboard_app", "ok": False, "msg": error})
        else:
            await _send(ws, {"action": "clipboard_app", "ok": True, "app": app})
        return

    if action == "read_desktop_clipboard_url":
        loop = asyncio.get_event_loop()
        url, error = await loop.run_in_executor(None, desktop_actions.read_clipboard_url)
        await _send(ws, {"action": "clipboard_url", "ok": not error, "url": url or "", "msg": error or ""})
        return

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
                _usb_targets[ws] = hwnd
                log.info("USB pick_target: [" + str(hwnd) + "] " + title)
                await _send(ws, {"action": "target_changed", "hwnd": hwnd, "title": title})
            except Exception as e:
                log.exception("USB do_pick: " + str(e))

        asyncio.ensure_future(do_pick())
        return

    if action == "type":
        text = str(msg.get("text", ""))
        if len(text) > 5000:
            await _send(ws, {"action": "error", "msg": "text too long"})
            return
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, keytrigger.input_text, text)
        await _send(ws, {"action": "type_done", "text": text, **result})
        return

    if action == "simulate_key":
        modifiers = msg.get("modifiers", []) or []
        key = msg.get("key", "")
        loop = asyncio.get_event_loop()
        ok = await loop.run_in_executor(None, keytrigger.simulate_key, modifiers, key)
        log.info("USB simulate_key: mods=" + str(modifiers) + " key=" + repr(key) + " ok=" + str(ok))
        await _send(ws, {"action": "simulate_key_ack", "modifiers": modifiers, "key": key, "ok": ok})
        return

    if action == "mouse":
        op = str(msg.get("op", ""))
        loop = asyncio.get_event_loop()
        try:
            if op == "move":
                # SendInput is a very small native call. Keeping relative moves
                # on the event loop avoids one thread-pool hop per touch frame.
                mouse.move(int(msg.get("dx", 0)), int(msg.get("dy", 0)))
                return
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
                return
            else:
                await _send(ws, {"action": "error", "msg": "unknown mouse op: " + repr(op)})
                return
            await _send(ws, {"action": "mouse_ack", "op": op})
        except Exception as e:
            log.exception("USB mouse error: " + str(e))
            await _send(ws, {"action": "error", "msg": "mouse failed: " + str(e)})
        return

    if action == "timeline_control":
        loop = asyncio.get_event_loop()
        ok, error = await loop.run_in_executor(
            None,
            timeline_control.execute,
            str(msg.get("op", "")),
            msg.get("delta", 0),
            _usb_targets.get(ws, 0),
        )
        if not ok:
            await _send(ws, {"action": "timeline_control_error", "msg": error})
        return

    # ---- trigger named shortcut (panel builtin buttons: copy/paste etc) ----
    if action == "shortcut":
        name = str(msg.get("name", ""))
        if not name:
            await _send(ws, {"action": "shortcut_ack", "ok": False, "msg": "missing name"})
            return
        try:
            ck_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "custom_keys.json")
            with open(ck_path, "r", encoding="utf-8") as _f:
                _ck = json.loads(_f.read())
            spec = None
            for _k in (_ck.get("keys") or []):
                if _k.get("id") == name or _k.get("label") == name:
                    spec = _k
                    break
            if not spec:
                await _send(ws, {"action": "shortcut_ack", "ok": False, "name": name, "msg": "unknown shortcut"})
                return
            mods = spec.get("modifiers", []) or []
            k = str(spec.get("key", ""))
            loop = asyncio.get_event_loop()
            ok = await loop.run_in_executor(None, keytrigger.simulate_key, mods, k)
            log.info("USB shortcut: name=" + name + " mods=" + str(mods) + " key=" + k + " ok=" + str(ok))
            await _send(ws, {"action": "shortcut_ack", "ok": ok, "name": name})
        except Exception as e:
            log.exception("USB shortcut error")
            await _send(ws, {"action": "shortcut_ack", "ok": False, "name": name, "msg": str(e)})
        return

    if action == "trigger_slot":
        log.info("USB trigger_slot raw msg: " + json.dumps(msg, ensure_ascii=False))
        slot_id = str(msg.get("id", ""))
        if not slot_id:
            await _send(ws, {"action": "trigger_ack", "ok": False, "msg": "missing id"})
            return
        try:
            data = layouts_loader.load()
        except Exception as e:
            log.exception("USB trigger_slot load layouts fail")
            await _send(ws, {"action": "trigger_ack", "ok": False, "id": slot_id, "msg": "load fail: " + str(e)})
            return
        target = None
        for lay in (data.get("layouts") or []):
            for page in (lay.get("pages") or []):
                for slot in (page.get("slots") or []):
                    k = slot.get("key")
                    if k and k.get("id") == slot_id:
                        target = slot
                        break
                if target:
                    break
            if target:
                break
        if not target:
            payload_target = msg.get("slot") or (msg.get("id") if isinstance(msg.get("id"), dict) else None)
            payload_type = ((payload_target or {}).get("key") or {}).get("type")
            if payload_type in {"link", "app", "codex"}:
                await _send(ws, {"action": "trigger_ack", "ok": False, "id": slot_id, "msg": "请先保存此按键后再使用"})
                return
            target = payload_target
        if not target:
            await _send(ws, {"action": "trigger_ack", "ok": False, "id": slot_id, "msg": "slot not found"})
            return
        key = target.get("key", {}) or {}
        key_type = key.get("type", "shortcut")
        loop = asyncio.get_event_loop()
        try:
            if key_type == "shortcut":
                sc = key.get("shortcut", {}) or {}
                mods = sc.get("modifiers", []) or []
                k = sc.get("key", "")
                log.info("USB trigger_slot shortcut: " + str(mods) + "+" + str(k))
                await loop.run_in_executor(None, keytrigger.simulate_key, mods, k)
                await _send(ws, {"action": "trigger_ack", "ok": True, "id": slot_id, "type": "shortcut"})
            elif key_type == "text":
                text = (key.get("text", {}) or {}).get("value", "")
                log.info("USB trigger_slot text: " + repr(text))
                result = await loop.run_in_executor(None, keytrigger.input_text, text)
                await _send(ws, {"action": "trigger_ack", "id": slot_id, "type": "text", **result})
            elif key_type == "macro":
                macro = key.get("macro", {}) or {}
                steps = macro.get("steps", []) or []
                log.info("USB trigger_slot macro: " + str(len(steps)) + " steps")
                await server._execute_macro(ws, steps, macro.get("interval_ms", 50))
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
                log.info("USB trigger_slot mouse: " + m_op)
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
                await _send(ws, {"action": "trigger_ack", "ok": False, "id": slot_id, "msg": "unknown type: " + str(key_type)})
        except Exception as e:
            log.exception("USB trigger_slot exec fail")
            await _send(ws, {"action": "trigger_ack", "ok": False, "id": slot_id, "msg": type(e).__name__ + ": " + str(e)})
        return


    # ---- 切换激活布局（面板页切换模板）----
    if action == "set_active":
        layout_id = str(msg.get("layout_id", ""))
        page_id = msg.get("page_id")
        if not layout_id:
            await _send(ws, {"action": "set_active_ack", "ok": False, "msg": "missing layout_id"})
            return
        try:
            page_id_str = str(page_id) if page_id else None
            ok = layouts_loader.set_active(layout_id, page_id_str)
            log.info("USB set_active: layout=" + layout_id + " page=" + str(page_id_str) + " ok=" + str(ok))
            await _send(ws, {"action": "set_active_ack", "ok": ok, "layout_id": layout_id, "page_id": page_id_str})
        except Exception as e:
            log.exception("USB set_active fail")
            await _send(ws, {"action": "set_active_ack", "ok": False, "layout_id": layout_id, "msg": str(e)})
        return

    # ---- 新建槽位 ----
    if action == "add_slot":
        layout_id = str(msg.get("layout_id", ""))
        page_id = str(msg.get("page_id", ""))
        slot = msg.get("slot") or {}
        if not layout_id or not page_id or not isinstance(slot, dict) or not slot.get("key"):
            await _send(ws, {"action": "add_slot_ack", "ok": False, "msg": "missing params"})
            return
        validation_error = _validate_key_definition(slot.get("key"))
        if validation_error:
            await _send(ws, {"action": "add_slot_ack", "ok": False, "msg": validation_error})
            return
        try:
            new_slot = layouts_loader.add_slot(layout_id, page_id, slot)
            if not new_slot:
                await _send(ws, {"action": "add_slot_ack", "ok": False, "msg": "page not found"})
                return
            log.info("USB add_slot: " + layout_id + "/" + page_id + " (" + str(new_slot.get("r")) + "," + str(new_slot.get("c")) + ") key=" + str(new_slot.get("key", {}).get("id")))
            await _send(ws, {"action": "add_slot_ack", "ok": True, "r": new_slot.get("r"), "c": new_slot.get("c"), "key_id": new_slot.get("key", {}).get("id")})
            await _push_layouts(ws)
        except Exception as e:
            log.exception("USB add_slot fail")
            await _send(ws, {"action": "add_slot_ack", "ok": False, "msg": str(e)})
        return

    # ---- 刷新布局（客户端触发）----
    if action == "reload_layouts":
        await _push_layouts(ws)
        return

    # ---- 更新槽位（编辑页保存）----
    if action == "update_slot":
        layout_id = str(msg.get("layout_id", ""))
        page_id = str(msg.get("page_id", ""))
        slot_r = int(msg.get("r", -1))
        slot_c = int(msg.get("c", -1))
        updates = msg.get("updates") or {}
        if not layout_id or not page_id or slot_r < 0 or slot_c < 0:
            await _send(ws, {"action": "update_slot_ack", "ok": False, "msg": "missing params"})
            return
        if "key" in updates:
            validation_error = _validate_key_definition(updates.get("key"))
            if validation_error:
                await _send(ws, {"action": "update_slot_ack", "ok": False, "msg": validation_error})
                return
        try:
            ok = layouts_loader.update_slot(layout_id, page_id, slot_r, slot_c, updates)
            log.info("USB update_slot: " + layout_id + "/" + page_id + " (" + str(slot_r) + "," + str(slot_c) + ") ok=" + str(ok))
            await _send(ws, {"action": "update_slot_ack", "ok": ok})
            await _push_layouts(ws)
        except Exception as e:
            log.exception("USB update_slot fail")
            await _send(ws, {"action": "update_slot_ack", "ok": False, "msg": str(e)})
        return

    # ---- 删除槽位 ----
    if action == "delete_slot":
        layout_id = str(msg.get("layout_id", ""))
        page_id = str(msg.get("page_id", ""))
        slot_r = int(msg.get("r", -1))
        slot_c = int(msg.get("c", -1))
        if not layout_id or not page_id or slot_r < 0 or slot_c < 0:
            await _send(ws, {"action": "delete_slot_ack", "ok": False, "msg": "missing params"})
            return
        try:
            ok = layouts_loader.delete_slot(layout_id, page_id, slot_r, slot_c)
            log.info("USB delete_slot: " + layout_id + "/" + page_id + " (" + str(slot_r) + "," + str(slot_c) + ") ok=" + str(ok))
            await _send(ws, {"action": "delete_slot_ack", "ok": ok})
            await _push_layouts(ws)
        except Exception as e:
            log.exception("USB delete_slot fail")
            await _send(ws, {"action": "delete_slot_ack", "ok": False, "msg": str(e)})
        return

    # ---- 安装预设 ----
    if action == "install_preset":
        preset_id = str(msg.get("preset_id", ""))
        if not preset_id:
            await _send(ws, {"action": "install_preset_ack", "ok": False, "msg": "missing preset_id"})
            return
        preset_path = os.path.join(layouts_loader.PRESETS_DIR, preset_id + ".json")
        if not os.path.isfile(preset_path):
            await _send(ws, {"action": "install_preset_ack", "ok": False, "msg": "preset not found: " + preset_id})
            return
        try:
            with open(preset_path, "r", encoding="utf-8") as pf:
                preset = json.load(pf)
            new_layout = layouts_loader.install_preset(preset)
            log.info("USB install_preset: " + preset_id + " -> " + str(new_layout.get("id")))
            await _send(ws, {"action": "install_preset_ack", "ok": True, "id": new_layout.get("id")})
            await _push_layouts(ws)
        except Exception as e:
            log.exception("USB install_preset fail")
            await _send(ws, {"action": "install_preset_ack", "ok": False, "msg": str(e)})
        return

    # ---- 改网格行列数 ----
    if action == "set_grid_rows":
        try:
            rows = int(msg.get("rows", 4))
            ok = layouts_loader.update_layout_field("__global__", "grid_rows", rows)
            await _send(ws, {"action": "set_grid_rows_ack", "ok": ok})
            if ok:
                await _push_layouts(ws)
        except Exception as e:
            await _send(ws, {"action": "set_grid_rows_ack", "ok": False, "msg": str(e)})
        return

    if action == "set_grid_cols":
        try:
            cols = int(msg.get("cols", 4))
            ok = layouts_loader.update_layout_field("__global__", "grid_cols", cols)
            await _send(ws, {"action": "set_grid_cols_ack", "ok": ok})
            if ok:
                await _push_layouts(ws)
        except Exception as e:
            await _send(ws, {"action": "set_grid_cols_ack", "ok": False, "msg": str(e)})
        return

    # ---- 新建模板 ----
    if action == "add_layout":
        layout_id = str(msg.get("id") or layouts_loader._gen_id(msg.get("name", "layout")))
        page_id = str(msg.get("page_id") or layouts_loader._gen_id("page"))
        try:
            new_layout = layouts_loader.add_layout({"id": layout_id, "name": msg.get("name", "新方案"), "icon": msg.get("icon", ""), "pages": [{"id": page_id, "name": "页面 1", "icon": "📄", "slots": []}]})
            if not new_layout:
                await _send(ws, {"action": "add_layout_ack", "ok": False, "msg": "layout already exists"})
                return
            await _send(ws, {"action": "add_layout_ack", "ok": True, "id": layout_id})
            await _push_layouts(ws)
        except Exception as e:
            log.exception("USB add_layout fail")
            await _send(ws, {"action": "add_layout_ack", "ok": False, "msg": str(e)})
        return

    # ---- 删除模板 ----
    if action == "delete_layout":
        layout_id = str(msg.get("layout_id", ""))
        if not layout_id:
            await _send(ws, {"action": "delete_layout_ack", "ok": False, "msg": "missing layout_id"})
            return
        try:
            ok = layouts_loader.delete_layout(layout_id)
            await _send(ws, {"action": "delete_layout_ack", "ok": ok})
            if ok:
                await _push_layouts(ws)
        except Exception as e:
            log.exception("USB delete_layout fail")
            await _send(ws, {"action": "delete_layout_ack", "ok": False, "msg": str(e)})
        return

    if action in {"archive_layout", "restore_layout"}:
        layout_id = str(msg.get("layout_id", ""))
        operation = layouts_loader.archive_layout if action == "archive_layout" else layouts_loader.restore_layout
        try:
            ok = bool(layout_id and operation(layout_id))
            await _send(ws, {"action": action + "_ack", "ok": ok, "layout_id": layout_id})
            if ok:
                await _push_layouts(ws)
        except Exception as e:
            log.exception(action + " fail")
            await _send(ws, {"action": action + "_ack", "ok": False, "msg": str(e)})
        return

    # ---- 重命名模板 ----
    if action == "rename_layout":
        layout_id = str(msg.get("layout_id", ""))
        name = str(msg.get("name", ""))
        icon = msg.get("icon")
        if not layout_id or not name:
            await _send(ws, {"action": "rename_layout_ack", "ok": False, "msg": "missing params"})
            return
        try:
            ok = layouts_loader.update_layout_field(layout_id, "name", name)
            if ok and icon:
                ok = layouts_loader.update_layout_field(layout_id, "icon", icon)
            await _send(ws, {"action": "rename_layout_ack", "ok": ok})
            if ok:
                await _push_layouts(ws)
        except Exception as e:
            await _send(ws, {"action": "rename_layout_ack", "ok": False, "msg": str(e)})
        return

    # ---- 新建页 ----
    if action == "add_page":
        layout_id = str(msg.get("layout_id", ""))
        if not layout_id:
            await _send(ws, {"action": "add_page_ack", "ok": False, "msg": "missing layout_id"})
            return
        try:
            new_page = layouts_loader.add_page(layout_id, {"name": msg.get("name", "新页"), "icon": msg.get("icon", "📄"), "slots": []})
            await _send(ws, {"action": "add_page_ack", "ok": True, "id": new_page.get("id") if new_page else None})
            await _push_layouts(ws)
        except Exception as e:
            await _send(ws, {"action": "add_page_ack", "ok": False, "msg": str(e)})
        return

    # ---- 删除页 ----
    if action == "delete_page":
        layout_id = str(msg.get("layout_id", ""))
        page_id = str(msg.get("page_id", ""))
        if not layout_id or not page_id:
            await _send(ws, {"action": "delete_page_ack", "ok": False, "msg": "missing params"})
            return
        try:
            ok = layouts_loader.delete_page(layout_id, page_id)
            await _send(ws, {"action": "delete_page_ack", "ok": ok})
            if ok:
                await _push_layouts(ws)
        except Exception as e:
            await _send(ws, {"action": "delete_page_ack", "ok": False, "msg": str(e)})
        return

    # ---- 重命名页 ----
    if action == "rename_page":
        layout_id = str(msg.get("layout_id", ""))
        page_id = str(msg.get("page_id", ""))
        name = str(msg.get("name", ""))
        icon = msg.get("icon")
        if not layout_id or not page_id or not name:
            await _send(ws, {"action": "rename_page_ack", "ok": False, "msg": "missing params"})
            return
        try:
            ok = layouts_loader.rename_page(layout_id, page_id, name, icon)
            await _send(ws, {"action": "rename_page_ack", "ok": ok})
            if ok:
                await _push_layouts(ws)
        except Exception as e:
            await _send(ws, {"action": "rename_page_ack", "ok": False, "msg": str(e)})
        return


    # ---- 自定义快捷键库 ----
    if action == "list_custom_keys":
        try:
            keys = custom_keys_loader.load()
            await _send(ws, {"action": "custom_keys", "keys": keys})
        except Exception as e:
            await _send(ws, {"action": "custom_keys", "keys": [], "error": str(e)})
        return

    if action == "add_custom_key":
        spec = msg.get("spec", {})
        if not isinstance(spec, dict):
            await _send(ws, {"action": "add_custom_key_ack", "ok": False, "msg": "spec must be object"})
            return
        try:
            new = custom_keys_loader.add(spec)
            await _send(ws, {"action": "add_custom_key_ack", "ok": True, "id": new.get("id")})
        except Exception as e:
            await _send(ws, {"action": "add_custom_key_ack", "ok": False, "msg": str(e)})
        return

    if action == "delete_custom_key":
        cid = str(msg.get("id", ""))
        if not cid:
            await _send(ws, {"action": "delete_custom_key_ack", "ok": False, "msg": "missing id"})
            return
        try:
            ok = custom_keys_loader.delete(cid)
            await _send(ws, {"action": "delete_custom_key_ack", "ok": ok})
        except Exception as e:
            await _send(ws, {"action": "delete_custom_key_ack", "ok": False, "msg": str(e)})
        return

    await _send(ws, {"action": "error", "msg": "unknown action: " + repr(action)})


async def handle_client(ws):
    try:
        ip_port = str(ws.remote_address)
    except Exception:
        ip_port = "?"
    log.info("USB 连接: " + ip_port)
    try:
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except Exception:
                await _send(ws, {"action": "error", "msg": "invalid json"})
                continue
            try:
                await _process_msg(ws, msg)
            except Exception as e:
                log.exception("USB msg 处理异常: " + str(e))
                try:
                    await _send(ws, {"action": "error", "msg": "server exception: " + type(e).__name__})
                except Exception:
                    pass
    except ConnectionClosed:
        pass
    except Exception as e:
        log.warning("USB 客户端异常: " + str(e))
    finally:
        recorder = server._recorders.pop(ws, None)
        if recorder:
            try: recorder.stop()
            except Exception: pass
        server._release_gamepad_keys(ws)
        server._release_held_mouse(ws)
        keytrigger.key_up("rctrl")
        _unregister_codex_client(ws)
        _usb_sessions.pop(ws, None)
        _usb_targets.pop(ws, None)
        log.info("USB 断开: " + ip_port)


async def run():
    log.info("USB WebSocket 监听 0.0.0.0:" + str(PORT))
    async with serve(handle_client, "0.0.0.0", PORT, max_size=64 * 1024):
        await asyncio.Future()


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        PORT = int(sys.argv[1])
    asyncio.run(run())

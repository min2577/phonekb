"""Bind PhoneKB slots to existing Codex Desktop threads via verified deeplinks."""

from __future__ import annotations

import ctypes
import json
import os
import re
import sqlite3
import threading
import time
from pathlib import Path
from typing import Optional

import codex_voice
import codex_approval
import keytrigger


CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
DEEPLINK_RE = re.compile(
    r"^codex://threads/([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})$"
)
REASONING_LABELS = {
    "low": ("轻度", "低", "Low"),
    "medium": ("中", "Medium"),
    "high": ("高", "High"),
    "xhigh": ("极高", "Extra high"),
}

_clipboard_lock = threading.RLock()


def _read_clipboard_text() -> Optional[str]:
    user32 = ctypes.windll.user32
    user32.OpenClipboard.argtypes = [ctypes.c_void_p]
    user32.OpenClipboard.restype = ctypes.c_bool
    user32.GetClipboardData.argtypes = [ctypes.c_uint]
    user32.GetClipboardData.restype = ctypes.c_void_p
    user32.CloseClipboard.argtypes = []
    user32.CloseClipboard.restype = ctypes.c_bool
    if not user32.OpenClipboard(None):
        return None
    try:
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        return ctypes.wstring_at(handle) if handle else None
    finally:
        user32.CloseClipboard()


def _write_clipboard_text(value: str) -> bool:
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    user32.OpenClipboard.argtypes = [ctypes.c_void_p]
    user32.OpenClipboard.restype = ctypes.c_bool
    user32.CloseClipboard.argtypes = []
    user32.CloseClipboard.restype = ctypes.c_bool
    user32.EmptyClipboard.argtypes = []
    user32.EmptyClipboard.restype = ctypes.c_bool
    user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
    user32.SetClipboardData.restype = ctypes.c_void_p
    kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalUnlock.restype = ctypes.c_bool
    payload = (str(value) + "\0").encode("utf-16-le")
    memory = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(payload))
    if not memory:
        return False
    pointer = kernel32.GlobalLock(memory)
    if not pointer:
        return False
    ctypes.memmove(pointer, payload, len(payload))
    kernel32.GlobalUnlock(memory)
    if not user32.OpenClipboard(None):
        return False
    try:
        if not user32.EmptyClipboard():
            return False
        return bool(user32.SetClipboardData(CF_UNICODETEXT, memory))
    finally:
        user32.CloseClipboard()


def _copy_current_deeplink() -> tuple[Optional[str], str]:
    """Use Codex's built-in Copy Deeplink command and restore text clipboard state."""
    with _clipboard_lock:
        previous = _read_clipboard_text()
        focused = codex_voice.focus_codex_composer()
        if not focused.get("ok"):
            return None, focused.get("msg") or "没有找到 Codex 当前任务"
        if not keytrigger.simulate_key(["ctrl", "alt"], "l"):
            return None, "无法触发 Codex 的复制任务链接命令"
        time.sleep(0.35)
        value = (_read_clipboard_text() or "").strip()
        if previous is not None:
            _write_clipboard_text(previous)
        match = DEEPLINK_RE.fullmatch(value)
        if not match:
            return None, "Codex 没有返回有效的任务链接，请确认当前显示的是任务页面"
        return value, ""


def _thread_metadata(thread_id: str) -> dict:
    sidebar_title = _sidebar_title(thread_id)
    db_path = Path.home() / ".codex" / "state_5.sqlite"
    if not db_path.is_file():
        return {"sidebar_title": sidebar_title} if sidebar_title else {}
    connection = None
    try:
        uri = db_path.resolve().as_uri() + "?mode=ro"
        connection = sqlite3.connect(uri, uri=True, timeout=1.0)
        row = connection.execute(
            "SELECT title, cwd, updated_at, rollout_path, reasoning_effort FROM threads WHERE id = ? LIMIT 1",
            (thread_id,),
        ).fetchone()
        if not row:
            return {"sidebar_title": sidebar_title} if sidebar_title else {}
        return {
            "sidebar_title": sidebar_title,
            "title": row[0] or "",
            "workspace": row[1] or "",
            "updated_at": row[2] or 0,
            "rollout_path": row[3] or "",
            "reasoning_effort": row[4] or "",
        }
    except Exception:
        return {"sidebar_title": sidebar_title} if sidebar_title else {}
    finally:
        if connection is not None:
            connection.close()


def _sidebar_title(thread_id: str) -> str:
    """Read the latest user-visible thread name from Codex's append-only index."""
    index_path = Path.home() / ".codex" / "session_index.jsonl"
    if not index_path.is_file():
        return ""
    latest = ""
    try:
        with index_path.open("r", encoding="utf-8") as stream:
            for line in stream:
                try:
                    item = json.loads(line)
                except (TypeError, ValueError):
                    continue
                if str(item.get("id") or "").lower() != thread_id.lower():
                    continue
                name = str(item.get("thread_name") or "").strip()
                if name:
                    latest = name
    except OSError:
        return ""
    return latest[:80]


def _open_deeplink(deeplink: str) -> None:
    os.startfile(deeplink)  # type: ignore[attr-defined]


def _parse_rollout_line(raw: bytes) -> Optional[dict]:
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None


def _status_from_item(item: dict) -> Optional[dict]:
    if item.get("type") != "event_msg":
        return None
    payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
    event_type = str(payload.get("type") or "")
    turn_id = str(payload.get("turn_id") or "")
    timestamp = str(item.get("timestamp") or "")
    if event_type == "task_started":
        return {"state": "running", "detail": "Codex 正在处理", "turn_id": turn_id, "status_updated_at": timestamp}
    if event_type == "task_complete":
        error = payload.get("error")
        if error:
            detail = str(error.get("message") or "任务执行失败") if isinstance(error, dict) else str(error)
            return {"state": "failed", "detail": detail, "turn_id": turn_id, "status_updated_at": timestamp}
        return {"state": "completed", "detail": "任务已完成", "turn_id": turn_id, "status_updated_at": timestamp}
    if event_type == "turn_aborted":
        interrupted = str(payload.get("reason") or "") == "interrupted"
        return {
            "state": "cancelled" if interrupted else "failed",
            "detail": "任务已停止" if interrupted else "任务异常中止",
            "turn_id": turn_id,
            "status_updated_at": timestamp,
        }
    return None


def _status_from_line(raw: bytes) -> Optional[dict]:
    item = _parse_rollout_line(raw)
    return _status_from_item(item) if item else None


class _RolloutStatusTracker:
    def __init__(self) -> None:
        self.lifecycle = {"state": "idle", "detail": "已绑定，等待 Codex 任务", "turn_id": "", "status_updated_at": ""}
        self.pending_inputs: dict[str, dict] = {}
        self.status = dict(self.lifecycle, attention_id="")

    def consume(self, raw: bytes) -> Optional[dict]:
        item = _parse_rollout_line(raw)
        if not item:
            return None
        lifecycle = _status_from_item(item)
        if lifecycle:
            self.lifecycle = lifecycle
            if lifecycle["state"] in ("running", "completed", "failed", "cancelled"):
                self.pending_inputs.clear()
            self.status = dict(lifecycle, attention_id="")
            return dict(self.status)

        if item.get("type") != "response_item":
            return None
        payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
        payload_type = str(payload.get("type") or "")
        call_id = str(payload.get("call_id") or "")
        timestamp = str(item.get("timestamp") or "")
        if payload_type == "function_call" and payload.get("name") == "request_user_input" and call_id:
            self.pending_inputs[call_id] = {"timestamp": timestamp}
            self.status = {
                "state": "waiting_input",
                "detail": "等待用户输入",
                "turn_id": str(self.lifecycle.get("turn_id") or ""),
                "attention_id": call_id,
                "status_updated_at": timestamp,
            }
            return dict(self.status)
        if payload_type != "function_call_output" or call_id not in self.pending_inputs:
            return None

        self.pending_inputs.pop(call_id, None)
        if self.pending_inputs:
            latest_call_id = next(reversed(self.pending_inputs))
            latest = self.pending_inputs[latest_call_id]
            self.status = {
                "state": "waiting_input",
                "detail": "等待用户输入",
                "turn_id": str(self.lifecycle.get("turn_id") or ""),
                "attention_id": latest_call_id,
                "status_updated_at": str(latest.get("timestamp") or timestamp),
            }
        else:
            self.status = dict(self.lifecycle, attention_id="", status_updated_at=timestamp)
        return dict(self.status)


def _latest_rollout_status(path: Path) -> dict:
    """Build the current state from lifecycle events and unresolved input calls."""
    tracker = _RolloutStatusTracker()
    try:
        with path.open("rb") as stream:
            for raw in stream:
                tracker.consume(raw)
    except OSError:
        pass
    return dict(tracker.status)


def _select_desktop_reasoning(effort: str) -> dict:
    labels = REASONING_LABELS.get(effort)
    if not labels:
        return {"ok": False, "msg": "不支持的推理强度"}
    try:
        window, composer = codex_voice._locate_codex_composer()  # type: ignore[attr-defined]
        codex_voice._activate_window(int(window.handle or 0))  # type: ignore[attr-defined]
        window.set_focus()

        composer_rect = composer.element_info.rectangle
        triggers = []
        all_labels = tuple(label for values in REASONING_LABELS.values() for label in values)
        for control in window.descendants(control_type="Button"):
            name = (control.window_text() or "").strip()
            rectangle = control.element_info.rectangle
            if not control.element_info.visible or not control.element_info.enabled:
                continue
            if rectangle.top < composer_rect.bottom - 20:
                continue
            if any(name.endswith(" " + label) for label in all_labels):
                triggers.append(control)
        if not triggers:
            return {"ok": False, "msg": "没有找到 Codex 的推理强度按钮"}

        trigger = max(triggers, key=lambda control: control.element_info.rectangle.bottom)
        trigger.click_input()
        time.sleep(0.25)
        effort_menus = [
            control for control in window.descendants(control_type="MenuItem")
            if (control.window_text() or "").strip().lower().startswith(("推理强度", "reasoning effort"))
            and control.element_info.visible
        ]
        if not effort_menus:
            keytrigger.simulate_key([], "esc")
            return {"ok": False, "msg": "Codex 没有打开推理强度菜单"}
        effort_menus[-1].click_input()
        time.sleep(0.25)

        choices = []
        for control in window.descendants(control_type="MenuItem"):
            name = (control.window_text() or "").strip()
            if control.element_info.visible and name in labels:
                choices.append(control)
        if not choices:
            keytrigger.simulate_key([], "esc")
            keytrigger.simulate_key([], "esc")
            return {"ok": False, "msg": "当前模型不支持该推理强度"}
        try:
            choices[0].invoke()
        except Exception:
            choices[0].iface_invoke.Invoke()

        for _ in range(12):
            time.sleep(0.1)
            for control in window.descendants(control_type="Button"):
                name = (control.window_text() or "").strip()
                if control.element_info.visible and any(name.endswith(" " + label) for label in labels):
                    return {"ok": True, "label": name}
        return {"ok": False, "msg": "Codex 没有确认推理强度已经改变"}
    except Exception as exc:
        keytrigger.simulate_key([], "esc")
        return {"ok": False, "msg": "无法操作 Codex 推理强度: " + str(exc)}


class CodexDesktopBindings:
    def __init__(self, state_path: Path):
        self.state_path = Path(state_path)
        self._lock = threading.RLock()
        self._bindings: dict[str, dict] = {}
        self._status_watchers: dict[str, dict] = {}
        self._approval_controller = codex_approval.CodexApprovalController()
        self._approval_status = {"pending": False, "ambiguous": False, "fingerprint": "", "slot": 0, "thread_id": "", "msg": ""}
        self._active_slot = 0
        self._load()

    def snapshot(self) -> dict:
        self.refresh_statuses()
        self.refresh_approval()
        with self._lock:
            changed = False
            for binding in self._bindings.values():
                if binding.get("custom_title"):
                    continue
                thread_id = str(binding.get("thread_id") or "")
                if not thread_id:
                    continue
                metadata = _thread_metadata(thread_id)
                title = str(metadata.get("sidebar_title") or metadata.get("title") or "").strip()[:80]
                if title and title != binding.get("title"):
                    binding["title"] = title
                    changed = True
                reasoning = str(metadata.get("reasoning_effort") or "")
                if reasoning in REASONING_LABELS and reasoning != binding.get("reasoning_effort"):
                    binding["reasoning_effort"] = reasoning
                    changed = True
            if changed:
                self._save_locked()
            result = {key: dict(value) for key, value in self._bindings.items()}
            approval = dict(self._approval_status)
            if approval.get("pending"):
                slot_key = str(approval.get("slot") or "")
                if slot_key in result:
                    result[slot_key]["state"] = "attention"
                    result[slot_key]["detail"] = approval.get("msg") or "Codex 正在等待批准"
                    result[slot_key]["approval"] = approval
            return result

    def approval_status(self) -> dict:
        with self._lock:
            return dict(self._approval_status)

    def refresh_approval(self) -> Optional[dict]:
        scanned = self._approval_controller.scan()
        with self._lock:
            slot = int(self._active_slot or 0)
            binding = self._bindings.get(str(slot)) if slot else None
            if scanned.get("pending") and binding:
                current = {
                    "pending": True,
                    "ambiguous": False,
                    "fingerprint": str(scanned.get("fingerprint") or ""),
                    "slot": slot,
                    "thread_id": str(binding.get("thread_id") or ""),
                    "msg": str(scanned.get("msg") or "Codex 正在等待批准终端操作"),
                }
            else:
                current = {
                    "pending": False,
                    "ambiguous": bool(scanned.get("ambiguous")),
                    "fingerprint": "",
                    "slot": slot if scanned.get("ambiguous") else 0,
                    "thread_id": str((binding or {}).get("thread_id") or "") if scanned.get("ambiguous") else "",
                    "msg": str(scanned.get("msg") or ""),
                }
            previous = self._approval_status
            comparable = ("pending", "ambiguous", "fingerprint", "slot", "thread_id", "msg")
            changed = any(previous.get(key) != current.get(key) for key in comparable)
            self._approval_status = current
            return dict(current) if changed else None

    def resolve_approval(self, slot: object, thread_id: object, fingerprint: object, decision: str) -> dict:
        action = "codex_approve_ack" if decision == "approve" else "codex_reject_ack"
        slot_number, error = self._slot_number(slot)
        if error:
            return {"action": action, "ok": False, "msg": error}
        with self._lock:
            binding = dict(self._bindings.get(str(slot_number)) or {})
            active_slot = int(self._active_slot or 0)
        if not binding:
            return {"action": action, "ok": False, "slot": slot_number, "msg": "请先长按任务槽绑定 Codex 任务"}
        expected_thread = str(binding.get("thread_id") or "")

        self.refresh_approval()
        with self._lock:
            approval = dict(self._approval_status)
        if not approval.get("pending") or approval.get("slot") != slot_number:
            return {"action": action, "ok": False, "slot": slot_number, "msg": approval.get("msg") or "当前没有待批准请求"}
        if active_slot != slot_number:
            return {"action": action, "ok": False, "slot": slot_number, "msg": "请先切换到要审批的任务槽"}
        if not thread_id or str(thread_id) != expected_thread:
            return {"action": action, "ok": False, "slot": slot_number, "msg": "任务已经变化，请刷新后重试"}
        if str(fingerprint or "") != str(approval.get("fingerprint") or ""):
            return {"action": action, "ok": False, "slot": slot_number, "msg": "审批请求已经变化，请刷新后重试"}

        result = self._approval_controller.resolve(decision, str(fingerprint))
        self.refresh_approval()
        return {
            "action": action,
            "ok": bool(result.get("ok")),
            "slot": slot_number,
            "thread_id": expected_thread,
            "msg": str(result.get("msg") or ""),
            "approval": self.approval_status(),
        }

    def refresh_statuses(self) -> list[dict]:
        changed_bindings = []
        with self._lock:
            changed = False
            for binding in self._bindings.values():
                status = self._read_binding_status_locked(binding)
                if not status:
                    continue
                previous = (binding.get("state"), binding.get("turn_id"), binding.get("attention_id"), binding.get("status_updated_at"))
                current = (status.get("state"), status.get("turn_id"), status.get("attention_id"), status.get("status_updated_at"))
                if previous == current:
                    continue
                binding.update(status)
                changed = True
                changed_bindings.append(dict(binding))
            if changed:
                self._save_locked()
        return changed_bindings

    def bind_current(self, slot: object) -> dict:
        slot_number, error = self._slot_number(slot)
        if error:
            return {"action": "codex_bind_current_slot_ack", "ok": False, "msg": error}
        deeplink, error = _copy_current_deeplink()
        if error or not deeplink:
            return {"action": "codex_bind_current_slot_ack", "ok": False, "slot": slot_number, "msg": error}
        thread_id = DEEPLINK_RE.fullmatch(deeplink).group(1).lower()  # type: ignore[union-attr]
        metadata = _thread_metadata(thread_id)
        title = str(metadata.get("sidebar_title") or metadata.get("title") or ("Codex 任务 " + thread_id[:8])).strip()[:80]
        workspace = str(metadata.get("workspace") or "").strip()[:500]
        binding = {
            "slot": slot_number,
            "thread_id": thread_id,
            "deeplink": deeplink,
            "title": title,
            "workspace": workspace,
            "rollout_path": str(metadata.get("rollout_path") or ""),
            "reasoning_effort": str(metadata.get("reasoning_effort") or "high"),
            "state": "idle",
            "detail": "已绑定，等待 Codex 任务",
            "turn_id": "",
            "attention_id": "",
            "status_updated_at": "",
            "bound_at": int(time.time()),
        }
        with self._lock:
            self._status_watchers.pop(thread_id, None)
            self._bindings[str(slot_number)] = binding
            self._active_slot = slot_number
            status = self._read_binding_status_locked(binding)
            if status:
                binding.update(status)
            self._save_locked()
        return {"action": "codex_bind_current_slot_ack", "ok": True, "slot": slot_number, "binding": dict(binding)}

    def focus(self, slot: object) -> dict:
        slot_number, error = self._slot_number(slot)
        if error:
            return {"action": "codex_focus_slot_ack", "ok": False, "msg": error}
        with self._lock:
            binding = dict(self._bindings.get(str(slot_number)) or {})
        deeplink = str(binding.get("deeplink") or "")
        if not DEEPLINK_RE.fullmatch(deeplink):
            return {"action": "codex_focus_slot_ack", "ok": False, "slot": slot_number, "msg": "任务槽还没有绑定 Codex 任务"}
        try:
            _open_deeplink(deeplink)
        except Exception as exc:
            return {"action": "codex_focus_slot_ack", "ok": False, "slot": slot_number, "msg": "无法打开 Codex 任务: " + str(exc)}
        with self._lock:
            self._active_slot = slot_number
            self._save_locked()
        # The deeplink was validated when the slot was bound. Opening it is
        # the requested action; clipboard/UIA verification used to delay the
        # ACK long after Codex had already switched tasks.
        return {
            "action": "codex_focus_slot_ack",
            "ok": True,
            "slot": slot_number,
            "binding": binding,
            "verified": False,
        }

    def rename(self, slot: object, title: object) -> dict:
        slot_number, error = self._slot_number(slot)
        if error:
            return {"action": "codex_rename_slot_ack", "ok": False, "msg": error}
        custom_title = str(title or "").strip()[:80]
        with self._lock:
            binding = self._bindings.get(str(slot_number))
            if not binding:
                return {
                    "action": "codex_rename_slot_ack",
                    "ok": False,
                    "slot": slot_number,
                    "msg": "任务槽还没有绑定 Codex 任务",
                }
            if custom_title:
                binding["custom_title"] = custom_title
                binding["title"] = custom_title
            else:
                binding.pop("custom_title", None)
                metadata = _thread_metadata(str(binding.get("thread_id") or ""))
                synced_title = str(metadata.get("sidebar_title") or metadata.get("title") or "").strip()[:80]
                if synced_title:
                    binding["title"] = synced_title
            self._save_locked()
            result = dict(binding)
        return {"action": "codex_rename_slot_ack", "ok": True, "slot": slot_number, "binding": result}

    def set_reasoning(self, slot: object, effort: object) -> dict:
        slot_number, error = self._slot_number(slot)
        if error:
            return {"action": "codex_set_desktop_reasoning_ack", "ok": False, "msg": error}
        reasoning = str(effort or "").strip().lower()
        if reasoning not in REASONING_LABELS:
            return {"action": "codex_set_desktop_reasoning_ack", "ok": False, "slot": slot_number, "msg": "推理强度无效"}
        with self._lock:
            binding = self._bindings.get(str(slot_number))
            if not binding:
                return {
                    "action": "codex_set_desktop_reasoning_ack",
                    "ok": False,
                    "slot": slot_number,
                    "msg": "请先长按任务槽绑定 Codex 任务",
                }
            if binding.get("state") == "running":
                return {
                    "action": "codex_set_desktop_reasoning_ack",
                    "ok": False,
                    "slot": slot_number,
                    "msg": "任务正在运行，请完成或停止后再调整下一轮推理强度",
                }

        focused = self.focus(slot_number)
        if not focused.get("ok"):
            return {
                "action": "codex_set_desktop_reasoning_ack",
                "ok": False,
                "slot": slot_number,
                "msg": focused.get("msg") or "无法切换到绑定任务",
            }
        selected = _select_desktop_reasoning(reasoning)
        if not selected.get("ok"):
            return {
                "action": "codex_set_desktop_reasoning_ack",
                "ok": False,
                "slot": slot_number,
                "msg": selected.get("msg") or "推理强度没有改变",
            }
        thread_id = str(binding.get("thread_id") or "")
        actual_reasoning = ""
        for _ in range(15):
            actual_reasoning = str(_thread_metadata(thread_id).get("reasoning_effort") or "")
            if actual_reasoning == reasoning:
                break
            time.sleep(0.1)
        if actual_reasoning != reasoning:
            return {
                "action": "codex_set_desktop_reasoning_ack",
                "ok": False,
                "slot": slot_number,
                "msg": "Codex 菜单已操作，但任务设置没有写入，仍为 " + (actual_reasoning or "未知"),
            }
        with self._lock:
            binding = self._bindings.get(str(slot_number))
            if not binding:
                return {"action": "codex_set_desktop_reasoning_ack", "ok": False, "slot": slot_number, "msg": "任务槽已解除绑定"}
            binding["reasoning_effort"] = reasoning
            self._save_locked()
            result = dict(binding)
        return {
            "action": "codex_set_desktop_reasoning_ack",
            "ok": True,
            "slot": slot_number,
            "reasoning_effort": reasoning,
            "binding": result,
        }

    def unbind(self, slot: object) -> dict:
        slot_number, error = self._slot_number(slot)
        if error:
            return {"action": "codex_unbind_slot_ack", "ok": False, "msg": error}
        with self._lock:
            removed = self._bindings.pop(str(slot_number), None)
            if self._active_slot == slot_number:
                self._active_slot = 0
            thread_id = str((removed or {}).get("thread_id") or "")
            if thread_id and not any(str(item.get("thread_id") or "") == thread_id for item in self._bindings.values()):
                self._status_watchers.pop(thread_id, None)
            self._save_locked()
        return {"action": "codex_unbind_slot_ack", "ok": True, "slot": slot_number}

    @staticmethod
    def _slot_number(value: object) -> tuple[int, str]:
        try:
            slot = int(value)
        except (TypeError, ValueError):
            return 0, "任务槽编号无效"
        if slot < 1 or slot > 6:
            return 0, "任务槽编号必须是 1 到 6"
        return slot, ""

    def _read_binding_status_locked(self, binding: dict) -> Optional[dict]:
        thread_id = str(binding.get("thread_id") or "")
        if not thread_id:
            return None
        rollout_path = str(binding.get("rollout_path") or "")
        if not rollout_path:
            metadata = _thread_metadata(thread_id)
            rollout_path = str(metadata.get("rollout_path") or "")
            if rollout_path:
                binding["rollout_path"] = rollout_path
        if not rollout_path:
            return None
        path = Path(rollout_path)
        try:
            file_size = path.stat().st_size
        except OSError:
            return None

        watcher = self._status_watchers.get(thread_id)
        if not watcher or watcher.get("path") != rollout_path or file_size < int(watcher.get("offset") or 0):
            tracker = _RolloutStatusTracker()
            try:
                with path.open("rb") as stream:
                    for raw in stream:
                        if not raw.endswith(b"\n"):
                            stream.seek(-len(raw), os.SEEK_CUR)
                            break
                        tracker.consume(raw)
                    offset = stream.tell()
            except OSError:
                return None
            self._status_watchers[thread_id] = {"path": rollout_path, "offset": offset, "tracker": tracker}
            return dict(tracker.status)

        offset = int(watcher.get("offset") or 0)
        if file_size == offset:
            return None
        try:
            with path.open("rb") as stream:
                stream.seek(offset)
                payload = stream.read(file_size - offset)
        except OSError:
            return None
        complete_end = payload.rfind(b"\n")
        if complete_end < 0:
            return None
        complete = payload[:complete_end + 1]
        watcher["offset"] = offset + len(complete)
        tracker = watcher.get("tracker")
        if not isinstance(tracker, _RolloutStatusTracker):
            self._status_watchers.pop(thread_id, None)
            return self._read_binding_status_locked(binding)
        latest = None
        for raw in complete.splitlines():
            status = tracker.consume(raw)
            if status:
                latest = status
        return latest

    def _load(self) -> None:
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
            bindings = raw.get("bindings") if isinstance(raw, dict) else None
            if isinstance(bindings, dict):
                self._bindings = {str(key): dict(value) for key, value in bindings.items() if isinstance(value, dict)}
            active_slot = int(raw.get("active_slot") or 0) if isinstance(raw, dict) else 0
            self._active_slot = active_slot if 1 <= active_slot <= 6 and str(active_slot) in self._bindings else 0
        except (OSError, ValueError):
            self._bindings = {}
            self._active_slot = 0

    def _save_locked(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        temporary.write_text(
            json.dumps({"bindings": self._bindings, "active_slot": self._active_slot}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temporary, self.state_path)

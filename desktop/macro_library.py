"""Persistent macro recording library used by the desktop comparison page."""
from __future__ import annotations

import json
import os
import time
import uuid


_DIR = os.path.dirname(os.path.abspath(__file__))
LIBRARY_FILE = os.path.join(_DIR, "macro_recordings.json")


def _normalize_macro(value):
    value = value if isinstance(value, dict) else {}
    steps = [dict(step) for step in value.get("steps", []) if isinstance(step, dict)]
    try:
        interval_ms = max(0, min(1000, int(value.get("interval_ms", 0))))
    except (TypeError, ValueError):
        interval_ms = 0
    return {"interval_ms": interval_ms, "steps": steps}


def load():
    try:
        with open(LIBRARY_FILE, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except (OSError, ValueError):
        return []
    items = raw.get("recordings", []) if isinstance(raw, dict) else []
    result = []
    for item in items:
        if not isinstance(item, dict):
            continue
        result.append({
            "id": str(item.get("id") or uuid.uuid4().hex),
            "name": str(item.get("name") or "未命名录制")[:80],
            "created_at": int(item.get("created_at") or 0),
            "macro": _normalize_macro(item.get("macro")),
        })
    return result


def save(items):
    payload = {"version": 1, "recordings": items}
    temp_path = LIBRARY_FILE + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp_path, LIBRARY_FILE)


def create(name, macro):
    return {
        "id": uuid.uuid4().hex,
        "name": str(name or "新录制")[:80],
        "created_at": int(time.time() * 1000),
        "macro": _normalize_macro(macro),
    }


def action_rows(macro):
    """Convert explicit wait steps into delays attached to the next action."""
    macro = _normalize_macro(macro)
    rows = []
    pending_delay = 0
    has_explicit_wait = False
    interval = macro["interval_ms"]
    pending_wait_indexes = []
    for step_index, step in enumerate(macro["steps"]):
        if step.get("type") == "wait_ms":
            has_explicit_wait = True
            pending_wait_indexes.append(step_index)
            try:
                pending_delay += max(0, int(step.get("value", 0)))
            except (TypeError, ValueError):
                pass
            continue
        delay = pending_delay if rows else 0
        if rows and not has_explicit_wait:
            delay = interval
        rows.append({
            "step": step,
            "step_index": step_index,
            "wait_indexes": list(pending_wait_indexes),
            "action": action_label(step),
            "delay_ms": delay,
        })
        pending_delay = 0
        has_explicit_wait = False
        pending_wait_indexes = []
    return rows


def action_label(step):
    step_type = str(step.get("type") or "")
    if step_type == "key":
        key = str(step.get("key") or "").upper()
        modifiers = [str(value).upper() for value in step.get("modifiers", [])]
        value = "+".join(modifiers + ([key] if key else [])) or "按键"
        mode = {"down": "按下", "up": "松开", "tap": "点按"}.get(step.get("mode"), "点按")
        duration = step.get("duration_ms")
        suffix = f"（{int(duration)} ms）" if duration is not None else ""
        return value + " · " + mode + suffix
    if step_type == "mouse":
        if step.get("op") == "wheel":
            return "滚轮向上" if int(step.get("delta", 120) or 120) > 0 else "滚轮向下"
        button = {"left": "鼠标左键", "right": "鼠标右键", "middle": "鼠标中键"}.get(step.get("button"), "鼠标")
        op = {"down": "按下", "up": "松开", "click": "点击"}.get(step.get("op"), "点击")
        duration = step.get("duration_ms")
        suffix = f"（{int(duration)} ms）" if duration is not None else ""
        return button + " · " + op + suffix
    if step_type == "text":
        return "文本 · " + str(step.get("value") or "")[:20]
    if step_type == "enter":
        return "ENTER · 点按"
    return step_type or "未知动作"


def statistics(macro):
    rows = action_rows(macro)
    delays = [row["delay_ms"] for row in rows[1:]]
    return {
        "actions": len(rows),
        "duration_ms": sum(delays),
        "average_ms": round(sum(delays) / len(delays), 1) if delays else 0,
        "maximum_ms": max(delays) if delays else 0,
    }

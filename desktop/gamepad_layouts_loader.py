"""Persistent single-layer layouts for the custom mobile control surface.

Layout version 3 stores each control's keyboard action directly in its slots.
Version 2 layouts are migrated on load by resolving their spatial/legacy key
objects once; newly saved layouts no longer contain a separate key layer.
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
import threading


_DIR = os.path.dirname(os.path.abspath(__file__))
_LOCK = threading.RLock()
_ALLOWED_TYPES = {"leftStick", "rightStick", "dpad", "abxy", "shoulder", "key", "mouse", "macro"}
_SLOTS = {
    "leftStick": ("up", "left", "down", "right"),
    "dpad": ("up", "left", "down", "right"),
    "abxy": ("a", "b", "x", "y"),
    "shoulder": ("press",),
    "key": ("press",),
    "macro": ("press",),
}
_SLOT_OFFSETS = {
    "up": (0, -13), "left": (-6, 0), "down": (0, 13), "right": (6, 0),
    "y": (0, -12), "x": (-6, 0), "a": (6, 0), "b": (0, 13), "press": (0, 0),
}
_MODIFIERS = ("ctrl", "shift", "alt", "win")
_KEY_ALIASES = {
    "control": "ctrl", "escape": "esc", " ": "space",
    "arrowup": "up", "arrowdown": "down", "arrowleft": "left", "arrowright": "right",
    "↑": "up", "↓": "down", "←": "left", "→": "right", "meta": "win", "super": "win",
}
_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?$")
_BACKGROUND_THEME_FIELDS = (
    "stage_top", "stage_bottom", "grid", "button_top", "button_bottom",
    "button_text", "button_border", "control_fill", "control_inner",
    "control_border", "accent",
)


def _write_root() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return _DIR


def _path() -> str:
    return os.path.join(_write_root(), "gamepad_layouts.json")


def _presets_path() -> str:
    return os.path.join(_write_root(), "gamepad_component_presets.json")


def _legacy_presets_path() -> str:
    return os.path.join(_write_root(), "gamepad_key_presets.json")


def _backgrounds_path() -> str:
    return os.path.join(_write_root(), "gamepad_background_presets.json")


def _copy(value):
    return json.loads(json.dumps(value, ensure_ascii=False))


def _limit(value, low, high, default):
    try:
        return max(low, min(high, float(value)))
    except (TypeError, ValueError):
        return default


def _minimum(value, low, default):
    """Normalize a numeric value with a lower bound but no product-level ceiling."""
    try:
        number = float(value)
        return max(low, number) if math.isfinite(number) else default
    except (TypeError, ValueError):
        return default


def _text(value, fallback, limit=48):
    value = str(value or "").strip()
    return value[:limit] if value else fallback


def _canonical_key(value):
    value = str(value or "").strip().lower()
    value = _KEY_ALIASES.get(value, value)
    return value[:32] if value else ""


def _normalize_binding(raw):
    """Return a direct key/shortcut binding or None."""
    if isinstance(raw, dict):
        key = _canonical_key(raw.get("key") or raw.get("value"))
        modifiers = []
        for value in raw.get("modifiers") or []:
            modifier = _canonical_key(value)
            if modifier in _MODIFIERS and modifier not in modifiers:
                modifiers.append(modifier)
        if not key:
            return None
        if modifiers or raw.get("type") == "shortcut":
            return {"type": "shortcut", "modifiers": modifiers, "key": key}
        return {"type": "key", "key": key}

    value = str(raw or "").strip()
    if not value:
        return None
    parts = [part.strip() for part in re.split(r"\s*\+\s*", value) if part.strip()]
    if not parts:
        return None
    modifiers = []
    main = ""
    for part in parts:
        key = _canonical_key(part)
        if key in _MODIFIERS and len(parts) > 1:
            if key not in modifiers:
                modifiers.append(key)
        else:
            main = key
    if not main and len(parts) == 1:
        main = _canonical_key(parts[0])
    if not main:
        return None
    if modifiers:
        return {"type": "shortcut", "modifiers": modifiers, "key": main}
    return {"type": "key", "key": main}


def _binding(value, *modifiers):
    return _normalize_binding({"key": value, "modifiers": list(modifiers)})


def _normalize_appearance(raw, default_shape):
    raw = raw if isinstance(raw, dict) else {}
    shape = str(raw.get("shape") or default_shape)
    if shape not in {"round", "pill", "square", "diamond"}:
        shape = default_shape
    result = {"shape": shape}
    skin = str(raw.get("skin") or "").strip()
    if skin in {"fluent", "matte", "arcade", "glass", "keycap", "hud", "skill", "pixel", "switch", "outline", "neon", "contrast"}:
        result["skin"] = skin
    label_mode = str(raw.get("labelMode") or "").strip()
    if label_mode in {"label", "key", "both"}:
        result["labelMode"] = label_mode
    press_effect = str(raw.get("pressEffect") or "").strip()
    if press_effect in {"sink", "scale", "glow", "none"}:
        result["pressEffect"] = press_effect
    for field in ("fill", "border", "text"):
        value = str(raw.get(field) or "").strip()
        if _COLOR_RE.match(value):
            result[field] = value
    return result


def _normalize_background(raw):
    raw = raw if isinstance(raw, dict) else {}
    result = {
        "id": _text(raw.get("id"), "mobile-light", 64),
        "name": _text(raw.get("name"), "", 48) if raw.get("name") else "",
    }
    base_id = str(raw.get("baseId") or raw.get("base_id") or "").strip()
    if base_id:
        result["baseId"] = base_id[:64]
    kind = str(raw.get("kind") or "").strip()
    if kind in {"mobile-light", "mobile", "terrain", "arcade", "paper"}:
        result["kind"] = kind
    theme_raw = raw.get("theme") if isinstance(raw.get("theme"), dict) else raw
    theme = {}
    for field in _BACKGROUND_THEME_FIELDS:
        value = str(theme_raw.get(field) or "").strip()
        if _COLOR_RE.match(value):
            theme[field] = value
    if theme:
        result["theme"] = theme
    return result


def _default_bindings(control_type):
    if control_type == "leftStick":
        return {"up": _binding("w"), "left": _binding("a"), "down": _binding("s"), "right": _binding("d")}
    if control_type == "dpad":
        return {"up": _binding("up"), "left": _binding("left"), "down": _binding("down"), "right": _binding("right")}
    if control_type == "abxy":
        return {"a": _binding("j"), "b": _binding("k"), "x": _binding("u"), "y": _binding("i")}
    if control_type == "macro":
        return {"press": _binding("s", "ctrl", "shift")}
    if control_type in {"shoulder", "key"}:
        return {"press": _binding("space")}
    return {}


def _control(control_id, control_type, label, x, y, bindings=None, **extra):
    item = {
        "id": control_id, "type": control_type, "label": label,
        "x": x, "y": y, "size": 100, "opacity": 100, "visible": True,
        "bindings": bindings if bindings is not None else _default_bindings(control_type),
    }
    item.update(extra)
    return item


def _default_data():
    controls = [
        _control("zl", "shoulder", "ZL", 5, 7, {"press": _binding("shift")}, variant="wide"),
        _control("l", "shoulder", "L", 6, 17, {"press": _binding("q")}, variant="wide"),
        _control("zr", "shoulder", "ZR", 84, 7, {"press": _binding("ctrl")}, variant="wide"),
        _control("r", "shoulder", "R", 84, 17, {"press": _binding("e")}, variant="wide"),
        _control("left-stick", "leftStick", "移动", 10, 67),
        _control("minus", "key", "减号", 37, 74, {"press": _binding("tab")}, size=72, variant="wide"),
        _control("capture", "key", "截图", 44, 74, {"press": _binding("f12")}, size=72, variant="wide"),
        _control("plus", "key", "加号", 56, 74, {"press": _binding("esc")}, size=72, variant="wide"),
        _control("home", "key", "主页", 63, 74, {"press": _binding("home")}, size=72, variant="wide"),
        _control("abxy", "abxy", "ABXY", 86, 62),
        _control("right-stick", "rightStick", "视角", 69, 68, {}, opacity=85, sensitivity=55),
    ]
    return {"version": 3, "activeLayoutId": "switch-standard", "layouts": [{
        "id": "switch-standard", "name": "Switch 标准布局", "icon": "◉",
        "controls": controls, "background": {"id": "mobile-light"},
        "canvas": {"width": 2400, "height": 1080},
    }]}


def _legacy_keys(raw):
    result = {}
    for item in raw.get("keys") or []:
        if not isinstance(item, dict):
            continue
        key_id = str(item.get("id") or "")
        if key_id:
            result[key_id] = {
                "value": item.get("value"),
                "x": _limit(item.get("x"), 0, 100, 50),
                "y": _limit(item.get("y"), 0, 100, 50),
            }
    return result


def _migrate_binding(control, slot, legacy):
    raw = (control.get("bindings") or {}).get(slot)
    if isinstance(raw, str) and raw in legacy:
        binding = _normalize_binding(legacy[raw].get("value"))
    else:
        binding = _normalize_binding(raw)
    if binding:
        return binding

    if not legacy:
        return None
    dx, dy = _SLOT_OFFSETS.get(slot, (0, 0))
    target_x = _limit(control.get("x"), 0, 100, 50) + dx
    target_y = _limit(control.get("y"), 0, 100, 50) + dy
    tolerance = max(5.0, _limit(control.get("size"), 50, 200, 100) * 0.14)
    nearest = None
    nearest_distance = float("inf")
    for item in legacy.values():
        distance = ((item["x"] - target_x) ** 2 + (item["y"] - target_y) ** 2) ** 0.5
        if distance <= tolerance and distance < nearest_distance:
            nearest, nearest_distance = item, distance
    return _normalize_binding(nearest.get("value")) if nearest else None


def _normalize_layout(raw, index):
    raw = raw if isinstance(raw, dict) else {}
    legacy = _legacy_keys(raw)
    controls, control_ids = [], set()
    for item in (raw.get("controls") or [])[:80]:
        if not isinstance(item, dict) or item.get("type") not in _ALLOWED_TYPES:
            continue
        control_type = item["type"]
        control_id = _text(item.get("id"), "control-" + str(len(controls) + 1), 64)
        if control_id in control_ids:
            continue
        control_ids.add(control_id)
        bindings = {}
        for slot in _SLOTS.get(control_type, ()):
            binding = _migrate_binding(item, slot, legacy)
            if binding:
                bindings[slot] = binding
        default_shape = "pill" if item.get("variant") == "wide" or control_type in {"shoulder", "macro"} else "round"
        control = {
            "id": control_id, "type": control_type,
            "label": _text(item.get("label"), "按键", 32),
            "x": round(_limit(item.get("x"), 0, 100, 50), 3),
            "y": round(_limit(item.get("y"), 0, 100, 50), 3),
            "size": round(_minimum(item.get("size"), 50, 100), 3),
            "opacity": round(_limit(item.get("opacity"), 10, 100, 100), 3),
            "visible": item.get("visible") is not False,
            "locked": bool(item.get("locked")),
            "bindings": bindings,
            "appearance": _normalize_appearance(item.get("appearance"), default_shape),
        }
        behavior = str(item.get("behavior") or "hold").strip()
        control["behavior"] = behavior if behavior in {"hold", "tap", "toggle"} else "hold"
        if item.get("variant") == "wide":
            control["variant"] = "wide"
        if control_type in {"rightStick", "mouse"}:
            control["sensitivity"] = round(_limit(item.get("sensitivity"), 1, 100, 55), 3)
            control["reticle"] = item.get("reticle") is not False
        controls.append(control)
    background_raw = raw.get("background") if isinstance(raw.get("background"), dict) else {}
    canvas_raw = raw.get("canvas") if isinstance(raw.get("canvas"), dict) else {}
    return {
        "id": _text(raw.get("id"), "layout-" + str(index + 1), 64),
        "name": _text(raw.get("name"), "未命名布局", 48),
        "icon": _text(raw.get("icon"), "◉", 8),
        "controls": controls,
        "background": _normalize_background(background_raw),
        "canvas": {
            "width": int(round(_limit(canvas_raw.get("width"), 640, 7680, 2400))),
            "height": int(round(_limit(canvas_raw.get("height"), 360, 4320, 1080))),
        },
    }


def normalize(raw):
    raw = raw if isinstance(raw, dict) else {}
    layouts = [_normalize_layout(layout, index) for index, layout in enumerate((raw.get("layouts") or [])[:30])]
    if not layouts:
        return _default_data()
    active = str(raw.get("activeLayoutId") or raw.get("active_layout_id") or layouts[0]["id"])
    if active not in {layout["id"] for layout in layouts}:
        active = layouts[0]["id"]
    return {"version": 3, "activeLayoutId": active, "layouts": layouts}


def load():
    with _LOCK:
        try:
            with open(_path(), "r", encoding="utf-8") as source:
                return normalize(json.load(source))
        except (OSError, ValueError, TypeError):
            return _default_data()


def save(raw):
    data = normalize(raw)
    path = _path()
    temporary = path + ".tmp"
    with _LOCK:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(temporary, "w", encoding="utf-8") as target:
            json.dump(data, target, ensure_ascii=False, indent=2)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, path)
    return _copy(data)


def _normalize_preset(raw, index):
    raw = raw if isinstance(raw, dict) else {}
    control = raw.get("control") if isinstance(raw.get("control"), dict) else {}
    legacy_keys = []
    for item in raw.get("keys") or []:
        if not isinstance(item, dict):
            continue
        migrated = dict(item)
        migrated["id"] = migrated.get("id") or "legacy-preset-key-" + str(len(legacy_keys) + 1)
        migrated["x"] = 50 + _limit(migrated.get("relativeX"), -100, 100, 0)
        migrated["y"] = 50 + _limit(migrated.get("relativeY"), -100, 100, 0)
        legacy_keys.append(migrated)
    layout = _normalize_layout({"controls": [dict(control, id="preset-control", x=50, y=50)], "keys": legacy_keys}, 0)
    if not layout["controls"]:
        return None
    return {
        "id": _text(raw.get("id"), "preset-" + str(index + 1), 64),
        "name": _text(raw.get("name"), "未命名组件预设", 48),
        "control": layout["controls"][0],
    }


def load_component_presets():
    """Load reusable single-layer component presets, including legacy files."""
    with _LOCK:
        data = None
        for path in (_presets_path(), _legacy_presets_path()):
            try:
                with open(path, "r", encoding="utf-8") as source:
                    data = json.load(source)
                break
            except (OSError, ValueError, TypeError):
                continue
    raw_presets = data.get("presets") if isinstance(data, dict) else []
    presets = []
    for index, raw in enumerate(raw_presets if isinstance(raw_presets, list) else []):
        preset = _normalize_preset(raw, index)
        if preset:
            presets.append(preset)
    return {"version": 2, "presets": presets[:80]}


def save_component_preset(preset):
    current = load_component_presets()
    item = _normalize_preset(preset, len(current["presets"]))
    if not item:
        raise ValueError("invalid component preset")
    presets = [value for value in current["presets"] if value.get("id") != item["id"]]
    presets.insert(0, item)
    data = {"version": 2, "presets": presets[:80]}
    path = _presets_path()
    temporary = path + ".tmp"
    with _LOCK:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(temporary, "w", encoding="utf-8") as target:
            json.dump(data, target, ensure_ascii=False, indent=2)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, path)
    return _copy(item)


def delete_component_preset(preset_id):
    current = load_component_presets()
    presets = [item for item in current["presets"] if item.get("id") != str(preset_id)]
    if len(presets) == len(current["presets"]):
        return False
    _write_json_atomic(_presets_path(), {"version": 2, "presets": presets})
    return True


def rename_component_preset(preset_id, name):
    current = load_component_presets()
    target = next((item for item in current["presets"] if item.get("id") == str(preset_id)), None)
    if not target:
        return None
    target["name"] = _text(name, target.get("name") or "未命名组件预设", 48)
    _write_json_atomic(_presets_path(), current)
    return _copy(target)


def _normalize_background_preset(raw, index):
    raw = raw if isinstance(raw, dict) else {}
    background = _normalize_background(raw)
    background["id"] = _text(raw.get("id"), "background-" + str(index + 1), 64)
    background["name"] = _text(raw.get("name"), "未命名背景", 48)
    return background


def load_background_presets():
    with _LOCK:
        try:
            with open(_backgrounds_path(), "r", encoding="utf-8") as source:
                raw = json.load(source)
        except (OSError, ValueError, TypeError):
            raw = {}
    presets = []
    for index, item in enumerate((raw.get("presets") or []) if isinstance(raw, dict) else []):
        if isinstance(item, dict):
            presets.append(_normalize_background_preset(item, index))
    return {"version": 1, "presets": presets[:80]}


def save_background_preset(preset):
    current = load_background_presets()
    item = _normalize_background_preset(preset, len(current["presets"]))
    presets = [value for value in current["presets"] if value.get("id") != item["id"]]
    presets.insert(0, item)
    _write_json_atomic(_backgrounds_path(), {"version": 1, "presets": presets[:80]})
    return _copy(item)


def delete_background_preset(preset_id):
    current = load_background_presets()
    presets = [item for item in current["presets"] if item.get("id") != str(preset_id)]
    if len(presets) == len(current["presets"]):
        return False
    _write_json_atomic(_backgrounds_path(), {"version": 1, "presets": presets})
    return True


def _write_json_atomic(path, data):
    temporary = path + ".tmp"
    with _LOCK:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(temporary, "w", encoding="utf-8") as target:
            json.dump(data, target, ensure_ascii=False, indent=2)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, path)


def set_active(layout_id):
    data = load()
    if str(layout_id) not in {layout["id"] for layout in data["layouts"]}:
        return False, data
    data["activeLayoutId"] = str(layout_id)
    return True, save(data)

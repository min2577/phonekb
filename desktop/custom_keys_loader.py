"""custom_keys_loader.py - read custom_keys.json and translate text keys to VK codes."""
import json
import os

_MOD_MAP = {
    "ctrl":  0xA2,
    "shift": 0xA0,
    "alt":   0xA4,
    "win":   0x5B,
}

_KEY_MAP = {
    "a": 0x41, "b": 0x42, "c": 0x43, "d": 0x44, "e": 0x45,
    "f": 0x46, "g": 0x47, "h": 0x48, "i": 0x49, "j": 0x4A,
    "k": 0x4B, "l": 0x4C, "m": 0x4D, "n": 0x4E, "o": 0x4F,
    "p": 0x50, "q": 0x51, "r": 0x52, "s": 0x53, "t": 0x54,
    "u": 0x55, "v": 0x56, "w": 0x57, "x": 0x58, "y": 0x59,
    "z": 0x5A,
    "0": 0x30, "1": 0x31, "2": 0x32, "3": 0x33, "4": 0x34,
    "5": 0x35, "6": 0x36, "7": 0x37, "8": 0x38, "9": 0x39,
    "/": 0xBF, "-": 0xBD, "=": 0xBB, ",": 0xBC, ".": 0xBE,
    ";": 0xBA, "'": 0xDE, "[": 0xDB, "]": 0xDD, "`": 0xC0,
    "f1":  0x70, "f2":  0x71, "f3":  0x72, "f4":  0x73,
    "f5":  0x74, "f6":  0x75, "f7":  0x76, "f8":  0x77,
    "f9":  0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
    "enter":     0x0D, "tab":       0x09, "space":     0x20,
    "backspace": 0x08, "delete":    0x2E, "escape":    0x1B,
    "home":      0x24, "end":       0x23,
    "pageup":    0x21, "pagedown":  0x22,
    "left":      0x25, "right":     0x27, "up": 0x26, "down": 0x28,
}

_CUSTOM_KEYS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "custom_keys.json")


def _translate(spec):
    try:
        mods = []
        for m in spec.get("modifiers", []):
            v = _MOD_MAP.get(m.lower())
            if v is None:
                return None
            mods.append(v)
        k = str(spec.get("key", "")).lower()
        vk = _KEY_MAP.get(k)
        if vk is None:
            return None
        return {
            "id": spec.get("id") or spec.get("label", "?"),
            "label": spec.get("label", "?"),
            "sub": spec.get("sub", ""),
            "modifiers": mods,
            "key": vk,
        }
    except Exception:
        return None


def load():
    if not os.path.exists(_CUSTOM_KEYS_FILE):
        return []
    try:
        with open(_CUSTOM_KEYS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        result = []
        for spec in data.get("keys", []):
            t = _translate(spec)
            if t:
                result.append(t)
        return result
    except Exception as e:
        print("[custom_keys] load failed: " + str(e), flush=True)
        return []


if __name__ == "__main__":
    keys = load()
    print("loaded", len(keys), "custom keys:")
    for k in keys:
        print(" -", k["label"], "sub=" + k["sub"], "mods=" + str(k["modifiers"]), "key=0x" + format(k["key"], "X"))


def _save(specs):
    """写 custom_keys.json（保留 _comment 字段）。"""
    try:
        with open(_CUSTOM_KEYS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    data["keys"] = specs
    try:
        with open(_CUSTOM_KEYS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print("[custom_keys] save failed:", e, flush=True)
        return False


def add(spec):
    """添加一个键。spec 包含 id/label/icon/modifiers/key(modifiers 是名字符串数组, key 是名字符串)。"""
    try:
        # 加载现有
        with open(_CUSTOM_KEYS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    specs = data.get("keys", [])
    # 验证 modifiers + key
    if not spec.get("modifiers") and not spec.get("key"):
        return False
    # id 冲突则重生成
    existing_ids = set(s.get("id") for s in specs)
    while spec["id"] in existing_ids:
        spec["id"] = spec["id"] + "_" + __import__("secrets").token_hex(2)
    specs.append({
        "id": spec["id"],
        "label": spec.get("label", ""),
        "icon": spec.get("icon", "⚡"),
        "modifiers": spec.get("modifiers", []),
        "key": spec.get("key", ""),
    })
    return _save(specs)


def update(spec_id, updates):
    """按 id 更新键字段。updates 是 dict，可以包含 label/icon/modifiers/key。"""
    try:
        with open(_CUSTOM_KEYS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return False
    specs = data.get("keys", [])
    for spec in specs:
        if spec.get("id") == spec_id:
            for k, v in updates.items():
                spec[k] = v
            return _save(specs)
    return False


def delete(spec_id):
    """按 id 删除键。返回 True 表示删除了，False 表示不存在。"""
    try:
        with open(_CUSTOM_KEYS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return False
    specs = data.get("keys", [])
    new_specs = [s for s in specs if s.get("id") != spec_id]
    if len(new_specs) == len(specs):
        return False
    return _save(new_specs)

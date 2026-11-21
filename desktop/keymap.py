# -*- coding: utf-8 -*-
"""keymap.py - 单一来源的 VK 码映射。

被 keytrigger.py（运行时触发）和 layouts_loader.py（add_v1 解析）共用。
"""
# 修饰键（含左右两侧，新名字 lctrl/rctrl 等；旧名字 ctrl/shift/alt/win 仍指左侧，向后兼容）
MOD_NAME_MAP = {
    # 旧名字（向后兼容）
    "ctrl": 0xA2, "control": 0xA2,
    "shift": 0xA0,
    "alt": 0xA4,
    "win": 0x5B, "meta": 0x5B,
    # 区分左右
    "lctrl": 0xA2, "rctrl": 0xA3,
    "lshift": 0xA0, "rshift": 0xA1,
    "lalt": 0xA4, "ralt": 0xA5,
    "lwin": 0x5B, "rwin": 0x5C,
}

# 完整 key 名 → VK 码
VK_NAME_MAP = {
    "backspace": 0x08, "tab": 0x09, "enter": 0x0D, "return": 0x0D,
    "caps": 0x14, "capslock": 0x14,
    "escape": 0x1B, "esc": 0x1B, "space": 0x20,
    "pageup": 0x21, "pgup": 0x21, "pagedown": 0x22, "pgdn": 0x22,
    "end": 0x23, "home": 0x24,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
    "delete": 0x2E, "del": 0x2E,
    "menu": 0x5D,
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73,
    "f5": 0x74, "f6": 0x75, "f7": 0x76, "f8": 0x77,
    "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
    # numpad
    "numpad0": 0x60, "numpad1": 0x61, "numpad2": 0x62, "numpad3": 0x63,
    "numpad4": 0x64, "numpad5": 0x65, "numpad6": 0x66, "numpad7": 0x67,
    "numpad8": 0x68, "numpad9": 0x69,
    "numpad_multiply": 0x6A, "numpad_add": 0x6B,
    "numpad_separator": 0x6C, "numpad_subtract": 0x6D,
    "numpad_decimal": 0x6E, "numpad_divide": 0x6F,
    # 媒体键（V2 增强）
    "volume_mute": 0xAD, "volume_down": 0xAE, "volume_up": 0xAF,
    "media_next": 0xB0, "media_prev": 0xB1, "media_play": 0xB3, "media_stop": 0xB2,
}

# 单字符 OEM 键
OEM_KEY_MAP = {
    "/": 0xBF, "-": 0xBD, "=": 0xBB, ",": 0xBC, ".": 0xBE,
    ";": 0xBA, "'": 0xDE, "[": 0xDB, "]": 0xDD, "`": 0xC0,
    "\\": 0xDC,
}

VK_SLEEP = 0x5F


def resolve_key(key):
    """key 名（str）或 ASCII 字符 → VK 码。失败返回 None。"""
    if key is None:
        return None
    s = str(key).lower()
    if s in VK_NAME_MAP:
        return VK_NAME_MAP[s]
    if len(s) == 1:
        c = ord(s)
        if 0x30 <= c <= 0x39:
            return c
        if 0x61 <= c <= 0x7A:
            # Windows virtual-key codes use the uppercase A-Z range even
            # when the requested key name is lowercase.
            return ord(s.upper())
        return OEM_KEY_MAP.get(s)
    return None


def resolve_mods(mod_list):
    """['ctrl','shift'] → [0xA2, 0xA0]；任一非法返回 None。"""
    if not mod_list:
        return []
    out = []
    for m in mod_list:
        v = MOD_NAME_MAP.get(str(m).lower())
        if v is None:
            return None
        out.append(v)
    return out

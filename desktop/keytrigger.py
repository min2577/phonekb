"""Keyboard injection helpers used by the desktop server.

The experimental ``scan`` backend emits hardware scan codes instead of only
virtual-key codes. It is still Windows ``SendInput`` (not a kernel HID
driver), but some games accept scan-code events that reject VK-only input.
Set ``PHONEKB_KEY_BACKEND=vk`` to restore the old behavior.
"""
import ctypes, os, time
from ctypes import wintypes
from keymap import MOD_NAME_MAP

user32 = ctypes.WinDLL("user32", use_last_error=True)

VK_BACK=0x08; VK_TAB=0x09; VK_RETURN=0x0D; VK_SHIFT=0x10
VK_CONTROL=0x11; VK_ALT=0x12; VK_ESCAPE=0x1B; VK_SPACE=0x20
VK_PRIOR=0x21; VK_NEXT=0x22; VK_END=0x23; VK_HOME=0x24
VK_LEFT=0x25; VK_UP=0x26; VK_RIGHT=0x27; VK_DOWN=0x28; VK_DELETE=0x2E
VK_INSERT=0x2D; VK_SNAPSHOT=0x2C; VK_PAUSE=0x13; VK_SCROLL=0x91
VK_CAPITAL=0x14; VK_APPS=0x5D
VK_LCONTROL=0xA2; VK_LSHIFT=0xA0; VK_LMENU=0xA4; VK_LWIN=0x5B
INPUT_KEYBOARD=1; KEYEVENTF_KEYUP=0x0002; KEYEVENTF_UNICODE=0x0004
KEYEVENTF_SCANCODE=0x0008; KEYEVENTF_EXTENDEDKEY=0x0001

_KEY_BACKEND = os.environ.get("PHONEKB_KEY_BACKEND", "scan").strip().lower()
if _KEY_BACKEND not in {"scan", "vk"}:
    _KEY_BACKEND = "scan"

try:
    user32.MapVirtualKeyW.argtypes = [wintypes.UINT, wintypes.UINT]
    user32.MapVirtualKeyW.restype = wintypes.UINT
    user32.VkKeyScanW.argtypes = [wintypes.WCHAR]
    user32.VkKeyScanW.restype = ctypes.c_short
except Exception:
    pass

# VK 码从 keymap.MOD_NAME_MAP 读（单一来源）

_CHAR_TO_VK = {}
for _i, _c in enumerate("abcdefghijklmnopqrstuvwxyz"): _CHAR_TO_VK[_c] = 0x41 + _i
for _i, _c in enumerate("0123456789"): _CHAR_TO_VK[_c] = 0x30 + _i
_CHAR_TO_VK.update({" ":VK_SPACE, "\t":VK_TAB, "\n":VK_RETURN, "-":0xBD, "=":0xBB, "[":0xDB, "]":0xDD, ";":0xBA, "'":0xDE, ",":0xBC, ".":0xBE, "/":0xBF, "\\":0xDC, "`":0xC0})

_KEY_NAME_TO_VK = {
    "enter":VK_RETURN, "return":VK_RETURN, "tab":VK_TAB, "space":VK_SPACE,
    "esc":VK_ESCAPE, "escape":VK_ESCAPE, "backspace":VK_BACK, "delete":VK_DELETE, "del":VK_DELETE,
    "caps":VK_CAPITAL, "capslock":VK_CAPITAL, "menu":VK_APPS,
    "insert":VK_INSERT, "printscreen":VK_SNAPSHOT, "pause":VK_PAUSE, "scrolllock":VK_SCROLL,
    "home":VK_HOME, "end":VK_END, "pageup":VK_PRIOR, "pgup":VK_PRIOR, "pagedown":VK_NEXT, "pgdn":VK_NEXT,
    "left":VK_LEFT, "right":VK_RIGHT, "up":VK_UP, "down":VK_DOWN,
}
for _i in range(1, 13): _KEY_NAME_TO_VK["f"+str(_i)] = 0x70 + (_i - 1)

def _resolve_modifier(name):
    return MOD_NAME_MAP.get(str(name).lower(), 0)

def _resolve_key(key):
    if isinstance(key, int):
        return key if 0 < key < 0xFF else 0
    s = str(key).lower().strip()
    if s in MOD_NAME_MAP: return MOD_NAME_MAP[s]
    if s in _KEY_NAME_TO_VK: return _KEY_NAME_TO_VK[s]
    if len(s) == 1 and s in _CHAR_TO_VK: return _CHAR_TO_VK[s]
    return 0

def key_down(key):
    """Hold one virtual key down for real-time gamepad input."""
    try:
        vk = _resolve_key(key)
        return bool(vk and _send_vk(vk, 0))
    except Exception:
        return False

def key_up(key):
    """Release one virtual key previously held by key_down()."""
    try:
        vk = _resolve_key(key)
        return bool(vk and _send_vk(vk, KEYEVENTF_KEYUP))
    except Exception:
        return False

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx",          wintypes.LONG),
        ("dy",          wintypes.LONG),
        ("mouseData",   wintypes.DWORD),
        ("dwFlags",     wintypes.DWORD),
        ("time",        wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG))]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg",    wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]

class _U(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]

class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _U)]

_EXTENDED_VKS = {
    0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28,
    0x2D, 0x2E, 0x5D, 0xA3, 0xA5,
}


def _send_vk(vk, flags=0):
    """Inject one key, using scan codes by default for better game support."""
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    if _KEY_BACKEND == "scan":
        scan = int(user32.MapVirtualKeyW(vk, 0) or 0)
        if scan:
            inp.ki.wVk = 0
            inp.ki.wScan = scan
            inp.ki.dwFlags = flags | KEYEVENTF_SCANCODE
            if vk in _EXTENDED_VKS:
                inp.ki.dwFlags |= KEYEVENTF_EXTENDEDKEY
        else:
            inp.ki.wVk = vk; inp.ki.wScan = 0; inp.ki.dwFlags = flags
    else:
        inp.ki.wVk = vk; inp.ki.wScan = 0; inp.ki.dwFlags = flags
    inp.ki.time = 0; inp.ki.dwExtraInfo = None
    return bool(user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp)))

def simulate_key(modifiers, key):
    try:
        mod_vks = [_resolve_modifier(m) for m in (modifiers or [])]
        mod_vks = [v for v in mod_vks if v]
        key_vk = _resolve_key(key) if key else 0
        if not mod_vks and key_vk == 0: return False  # 既没修饰键也没主键 = 无操作
        try: user32.AllowSetForegroundWindow(0xFFFFFFFF)
        except Exception: pass
        ok = True
        for m in mod_vks:
            ok = _send_vk(m, 0) and ok
            time.sleep(0.005)
        if key_vk != 0:
            ok = _send_vk(key_vk, 0) and ok
            time.sleep(0.02)
            ok = _send_vk(key_vk, KEYEVENTF_KEYUP) and ok
            time.sleep(0.005)
        for m in reversed(mod_vks):
            ok = _send_vk(m, KEYEVENTF_KEYUP) and ok
            time.sleep(0.005)
        return ok
    except Exception:
        return False


def _char_key_spec(char):
    """Return (modifiers, vk) for a character supported by the active layout."""
    if char == "\n" or char == "\r":
        return [], VK_RETURN
    if char == "\t":
        return [], VK_TAB
    try:
        encoded = int(user32.VkKeyScanW(char))
    except Exception:
        return None
    if encoded == -1:
        return None
    encoded &= 0xFFFF
    vk = encoded & 0xFF
    shift_state = (encoded >> 8) & 0xFF
    modifiers = []
    if shift_state & 1:
        modifiers.append(VK_SHIFT)
    if shift_state & 2:
        modifiers.append(VK_CONTROL)
    if shift_state & 4:
        modifiers.append(VK_ALT)
    return modifiers, vk


def type_text_keys(text):
    """Type text as physical key presses when every character is mappable."""
    specs = []
    for char in str(text or ""):
        spec = _char_key_spec(char)
        if spec is None:
            return False
        specs.append(spec)
    if not specs:
        return False
    for modifiers, vk in specs:
        for modifier in modifiers:
            if not _send_vk(modifier, 0):
                return False
            time.sleep(0.003)
        if not _send_vk(vk, 0):
            return False
        time.sleep(0.008)
        if not _send_vk(vk, KEYEVENTF_KEYUP):
            return False
        for modifier in reversed(modifiers):
            time.sleep(0.003)
            if not _send_vk(modifier, KEYEVENTF_KEYUP):
                return False
        time.sleep(0.006)
    return True


def _write_clipboard_text(text):
    """Replace the Windows clipboard with Unicode text."""
    value = str(text or "")
    if not value:
        return False
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.EmptyClipboard.argtypes = []
    user32.EmptyClipboard.restype = wintypes.BOOL
    user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    user32.SetClipboardData.restype = wintypes.HANDLE
    user32.CloseClipboard.argtypes = []
    user32.CloseClipboard.restype = wintypes.BOOL
    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = wintypes.LPVOID
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalUnlock.restype = wintypes.BOOL
    kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalFree.restype = wintypes.HGLOBAL

    payload = (value + "\0").encode("utf-16-le")
    handle = kernel32.GlobalAlloc(0x0002, len(payload))  # GMEM_MOVEABLE
    if not handle:
        return False
    pointer = kernel32.GlobalLock(handle)
    if not pointer:
        kernel32.GlobalFree(handle)
        return False
    ctypes.memmove(pointer, payload, len(payload))
    kernel32.GlobalUnlock(handle)

    opened = False
    for _ in range(6):
        if user32.OpenClipboard(None):
            opened = True
            break
        time.sleep(0.025)
    if not opened:
        kernel32.GlobalFree(handle)
        return False
    transferred = False
    try:
        if not user32.EmptyClipboard():
            return False
        if not user32.SetClipboardData(13, handle):  # CF_UNICODETEXT
            return False
        transferred = True
        return True
    finally:
        user32.CloseClipboard()
        if not transferred:
            kernel32.GlobalFree(handle)


def paste_text(text):
    """Put text on the clipboard and paste it with the scan-code backend."""
    if not _write_clipboard_text(text):
        return False
    time.sleep(0.025)
    return simulate_key(["ctrl"], "v")


def input_text(text):
    """Send text using key presses, clipboard paste, then Unicode fallback."""
    value = str(text or "")
    if not value:
        return {"ok": False, "method": "empty", "sent": 0}
    if all(_char_key_spec(char) is not None for char in value):
        if type_text_keys(value):
            return {"ok": True, "method": "scan_keys", "sent": len(value)}
    if paste_text(value):
        return {"ok": True, "method": "clipboard_paste", "sent": len(value)}
    sent = type_text(value)
    return {"ok": sent >= len(value) * 2, "method": "unicode", "sent": sent}

def type_text(text):
    sent = 0
    if not text: return 0
    try: user32.AllowSetForegroundWindow(0xFFFFFFFF)
    except Exception: pass
    for ch in text:
        try:
            for is_up in (0, KEYEVENTF_KEYUP):
                inp = INPUT()
                inp.type = INPUT_KEYBOARD
                inp.ki.wVk = 0; inp.ki.wScan = ord(ch); inp.ki.dwFlags = KEYEVENTF_UNICODE | is_up
                inp.ki.time = 0; inp.ki.dwExtraInfo = None
                if user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp)): sent += 1
            time.sleep(0.005)
        except Exception: pass
    return sent

def focus_window(hwnd):
    if not hwnd: return False
    try:
        fg = user32.GetForegroundWindow()
        if fg == hwnd: return True
        if user32.IsIconic(hwnd): user32.ShowWindow(hwnd, 9)
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.05)
        return user32.GetForegroundWindow() == hwnd
    except Exception: return False

def get_foreground_hwnd():
    return user32.GetForegroundWindow()

if __name__ == "__main__":
    print("ctrl+c:", simulate_key(["ctrl"], "c"))
    print("enter:", simulate_key([], "enter"))

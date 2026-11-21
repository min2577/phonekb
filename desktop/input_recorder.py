"""Windows low-level keyboard/mouse recorder for macro editing.

Records only key transitions, mouse buttons, and wheel input. Pointer movement
is intentionally ignored so a short game interaction stays editable.
"""
import ctypes
import threading
import time
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
ULONG_PTR = ctypes.c_void_p
LRESULT = ctypes.c_ssize_t
HHOOK = wintypes.HHOOK if hasattr(wintypes, "HHOOK") else ctypes.c_void_p

# ctypes 默认把 WinAPI 返回值当作 32 位 int；在 64 位 Windows 下会截断钩子句柄，
# 导致 SetWindowsHookExW 看起来失败或后续无法卸载。显式声明指针类型。
user32.SetWindowsHookExW.argtypes = [ctypes.c_int, ctypes.c_void_p, wintypes.HINSTANCE, wintypes.DWORD]
user32.SetWindowsHookExW.restype = HHOOK
user32.UnhookWindowsHookEx.argtypes = [HHOOK]
user32.UnhookWindowsHookEx.restype = wintypes.BOOL
user32.CallNextHookEx.argtypes = [HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
user32.CallNextHookEx.restype = LRESULT
user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostThreadMessageW.restype = wintypes.BOOL
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.GetCurrentThreadId.restype = wintypes.DWORD

WH_KEYBOARD_LL = 13
WH_MOUSE_LL = 14
WM_QUIT = 0x0012
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_MBUTTONDOWN = 0x0207
WM_MBUTTONUP = 0x0208
WM_MOUSEWHEEL = 0x020A
LLKHF_INJECTED = 0x00000010
LLMHF_INJECTED = 0x00000001
MAPVK_VSC_TO_VK_EX = 3
TAP_MAX_MS = 250


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", POINT),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

_SPECIAL = {
    0x08: "backspace", 0x09: "tab", 0x0D: "enter", 0x14: "capslock",
    0x1B: "escape", 0x20: "space", 0x21: "pageup", 0x22: "pagedown",
    0x23: "end", 0x24: "home", 0x25: "left", 0x26: "up", 0x27: "right",
    0x28: "down", 0x2C: "printscreen", 0x2D: "insert", 0x2E: "delete",
    0x13: "pause", 0x91: "scrolllock",
}
_OEM = {0xBF: "/", 0xBD: "-", 0xBB: "=", 0xBC: ",", 0xBE: ".", 0xBA: ";", 0xDE: "'", 0xDB: "[", 0xDD: "]", 0xC0: "`", 0xDC: "\\"}


def _key_name(vk, scan, flags):
    # 低级钩子在不同键盘/Windows 版本上可能给 Shift 返回 VK_SHIFT(0x10)，
    # 也可能直接返回 VK_LSHIFT/VK_RSHIFT(0xA0/0xA1)。统一成宏编辑器使用的名称。
    if vk in (0x10, 0xA0, 0xA1):
        if vk == 0xA1 or scan == 0x36:
            return "rshift"
        return "lshift"
    if vk in (0x11, 0xA2, 0xA3):
        if vk == 0xA3 or (flags & 0x01):
            return "rctrl"
        return "lctrl"
    if vk in (0x12, 0xA4, 0xA5):
        if vk == 0xA5 or (flags & 0x20):
            return "ralt"
        return "lalt"
    if vk == 0x5B:
        return "lwin"
    if vk == 0x5C:
        return "rwin"
    if 0x41 <= vk <= 0x5A:
        return chr(vk).lower()
    if 0x30 <= vk <= 0x39:
        return chr(vk)
    if 0x70 <= vk <= 0x7B:
        return "f" + str(vk - 0x6F)
    if 0x60 <= vk <= 0x69:
        return "numpad" + str(vk - 0x60)
    if vk in _SPECIAL:
        return _SPECIAL[vk]
    if vk in _OEM:
        return _OEM[vk]
    return "vk_" + format(vk, "02x")


def _signed_word(value):
    value = int(value) & 0xFFFF
    return value - 0x10000 if value & 0x8000 else value


class InputRecorder:
    def __init__(self, stop_key=None, on_stop=None):
        self._lock = threading.Lock()
        self._thread = None
        self._thread_id = 0
        self._ready = threading.Event()
        self._stopped = threading.Event()
        self._events = []
        self._started_at = 0.0
        self._keyboard_hook = None
        self._mouse_hook = None
        self._hook_error = ""
        self._stop_key = str(stop_key or "").lower()
        self._on_stop = on_stop
        self._stop_requested = False
        self._keyboard_proc = HOOKPROC(self._keyboard_callback)
        self._mouse_proc = HOOKPROC(self._mouse_callback)

    @property
    def recording(self):
        return bool(self._thread and self._thread.is_alive())

    def start(self):
        if self.recording:
            return False, "已经在录制"
        with self._lock:
            self._events = []
            self._started_at = time.perf_counter()
        self._ready.clear()
        self._stopped.clear()
        self._hook_error = ""
        self._stop_requested = False
        self._thread = threading.Thread(target=self._run, name="phonekb-input-recorder", daemon=True)
        self._thread.start()
        if not self._ready.wait(1.5):
            self.stop()
            return False, "无法安装键盘鼠标监听"
        if self._hook_error:
            self.stop()
            return False, self._hook_error
        return True, ""

    def stop(self):
        thread = self._thread
        if not thread:
            return self._macro()
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        thread.join(2.0)
        self._thread = None
        self._thread_id = 0
        self._stopped.set()
        return self._macro()

    def _append(self, event):
        now = time.perf_counter()
        with self._lock:
            delay = max(0.0, now - self._started_at)
            self._started_at = now
            self._events.append((delay, event))

    def _keyboard_callback(self, code, message, data):
        if code >= 0 and message in (WM_KEYDOWN, WM_KEYUP, WM_SYSKEYDOWN, WM_SYSKEYUP):
            item = ctypes.cast(data, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            if not (item.flags & LLKHF_INJECTED):
                name = _key_name(item.vkCode, item.scanCode, item.flags)
                mode = "down" if message in (WM_KEYDOWN, WM_SYSKEYDOWN) else "up"
                if self._stop_key and name == self._stop_key:
                    if mode == "down" and not self._stop_requested:
                        self._stop_requested = True
                        if self._on_stop:
                            try:
                                self._on_stop()
                            except Exception:
                                pass
                    return user32.CallNextHookEx(None, code, message, data)
                self._append({"type": "key", "mode": mode, "modifiers": [], "key": name})
        return user32.CallNextHookEx(None, code, message, data)

    def _mouse_callback(self, code, message, data):
        if code >= 0:
            item = ctypes.cast(data, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
            if not (item.flags & LLMHF_INJECTED):
                values = {
                    WM_LBUTTONDOWN: ("left", "down"), WM_LBUTTONUP: ("left", "up"),
                    WM_RBUTTONDOWN: ("right", "down"), WM_RBUTTONUP: ("right", "up"),
                    WM_MBUTTONDOWN: ("middle", "down"), WM_MBUTTONUP: ("middle", "up"),
                }
                if message in values:
                    button, op = values[message]
                    self._append({"type": "mouse", "op": op, "button": button})
                elif message == WM_MOUSEWHEEL:
                    delta = _signed_word(item.mouseData >> 16)
                    self._append({"type": "mouse", "op": "wheel", "delta": 120 if delta >= 0 else -120})
        return user32.CallNextHookEx(None, code, message, data)

    def _run(self):
        self._thread_id = kernel32.GetCurrentThreadId()
        self._keyboard_hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._keyboard_proc, kernel32.GetModuleHandleW(None), 0)
        self._mouse_hook = user32.SetWindowsHookExW(WH_MOUSE_LL, self._mouse_proc, kernel32.GetModuleHandleW(None), 0)
        if not self._keyboard_hook or not self._mouse_hook:
            self._hook_error = "无法安装键盘鼠标监听，请用管理员权限重启桌面端"
            if self._keyboard_hook: user32.UnhookWindowsHookEx(self._keyboard_hook)
            if self._mouse_hook: user32.UnhookWindowsHookEx(self._mouse_hook)
            self._ready.set()
            return
        self._ready.set()
        message = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(message))
            user32.DispatchMessageW(ctypes.byref(message))
        user32.UnhookWindowsHookEx(self._keyboard_hook)
        user32.UnhookWindowsHookEx(self._mouse_hook)
        self._keyboard_hook = None
        self._mouse_hook = None

    def _macro(self):
        with self._lock:
            events = list(self._events)
        events = self._consolidate_taps(events)
        steps = []
        for delay, event in events:
            if steps:
                steps.append({"type": "wait_ms", "value": max(0, min(60000, int(round(delay * 1000))))})
            steps.append(event)
        return {"interval_ms": 0, "steps": steps}

    @staticmethod
    def _consolidate_taps(events):
        """Merge a short down/up pair into one tap or mouse click.

        Delays are stored between raw events. When the release is removed, its
        delay is carried forward so the timing of the following action stays
        unchanged. Long presses and pairs separated by another action remain
        explicit down/up events.
        """
        output = []
        carry_delay = 0.0
        index = 0
        while index < len(events):
            delay, event = events[index]
            delay += carry_delay
            carry_delay = 0.0
            if index + 1 < len(events):
                next_delay, next_event = events[index + 1]
                if next_delay * 1000 <= TAP_MAX_MS and InputRecorder._is_matching_release(event, next_event):
                    tap = dict(event)
                    tap["duration_ms"] = max(0, min(60000, int(round(next_delay * 1000))))
                    if event.get("type") == "key":
                        tap["mode"] = "tap"
                    else:
                        tap["op"] = "click"
                    output.append((delay, tap))
                    carry_delay = next_delay
                    index += 2
                    continue
            output.append((delay, event))
            index += 1
        return output

    @staticmethod
    def _is_matching_release(press, release):
        if not isinstance(press, dict) or not isinstance(release, dict):
            return False
        if press.get("type") != release.get("type"):
            return False
        if press.get("type") == "key":
            return (press.get("mode") == "down" and release.get("mode") == "up"
                    and press.get("key") == release.get("key")
                    and list(press.get("modifiers") or []) == list(release.get("modifiers") or []))
        if press.get("type") == "mouse":
            return (press.get("op") == "down" and release.get("op") == "up"
                    and press.get("button") == release.get("button"))
        return False

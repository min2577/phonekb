"""Small Windows global hotkey listener for the desktop macro page."""
from __future__ import annotations
import ctypes
import threading
from ctypes import wintypes
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
VK_F8 = 0x77
user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
user32.RegisterHotKey.restype = wintypes.BOOL
user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
user32.UnregisterHotKey.restype = wintypes.BOOL
user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostThreadMessageW.restype = wintypes.BOOL
user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
user32.GetMessageW.restype = wintypes.BOOL
class GlobalHotkey(threading.Thread):
    def __init__(self, callback, key=VK_F8, hotkey_id=0x504B):
        super().__init__(name="phonekb-global-hotkey", daemon=True)
        self._callback, self._key, self._id = callback, int(key), int(hotkey_id)
        self._thread_id = 0
        self._ready = threading.Event()
        self.registered = False
    def run(self):
        self._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        self.registered = bool(user32.RegisterHotKey(None, self._id, 0, self._key))
        self._ready.set()
        if not self.registered: return
        message = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
            if message.message == WM_HOTKEY and int(message.wParam) == self._id:
                try: self._callback()
                except Exception: pass
        user32.UnregisterHotKey(None, self._id)
        self.registered = False
    def wait_ready(self, timeout=1.0):
        return self._ready.wait(timeout) and self.registered
    def stop(self):
        if self._thread_id: user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        self.join(1.5)

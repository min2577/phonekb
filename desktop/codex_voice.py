"""Find the Codex composer through UI Automation and inject speech text."""

import ctypes
import os
import time
from ctypes import wintypes

import keytrigger

try:
    from pywinauto import Desktop
except ImportError:  # The server still starts and returns a useful protocol error.
    Desktop = None


user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
GA_ROOT = 2
SW_RESTORE = 9
CODEX_TEST_PHRASE = "你的方案不错，直接开干。"
NEW_TASK_LABELS = {"新建任务", "New task"}

kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.LPWSTR,
    ctypes.POINTER(wintypes.DWORD),
]
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.GetCurrentThreadId.restype = wintypes.DWORD

user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
user32.AttachThreadInput.restype = wintypes.BOOL
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL
user32.BringWindowToTop.argtypes = [wintypes.HWND]
user32.BringWindowToTop.restype = wintypes.BOOL
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL


def _window_title(hwnd: int) -> str:
    if not hwnd:
        return ""
    length = user32.GetWindowTextLengthW(hwnd)
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value or "(无标题)"


def _process_image(process_id: int) -> str:
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(process_id or 0))
    if not handle:
        return ""
    try:
        size = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return ""
        return buffer.value
    finally:
        kernel32.CloseHandle(handle)


def _is_codex_host(process_path: str) -> bool:
    normalized = str(process_path or "").replace("/", "\\").lower()
    executable = os.path.basename(normalized)
    return executable == "chatgpt.exe" and ("\\openai.codex_" in normalized or "\\openai\\codex\\" in normalized)


def _activate_window(hwnd: int) -> None:
    """Bring a UIA-discovered window forward using its real HWND, never coordinates."""
    if not hwnd:
        return
    current_thread = int(kernel32.GetCurrentThreadId() or 0)
    foreground_hwnd = int(user32.GetForegroundWindow() or 0)
    foreground_thread = int(user32.GetWindowThreadProcessId(foreground_hwnd, None) or 0)
    attached = False
    try:
        if current_thread and foreground_thread and current_thread != foreground_thread:
            attached = bool(user32.AttachThreadInput(current_thread, foreground_thread, True))
        user32.ShowWindow(hwnd, SW_RESTORE)
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
    finally:
        if attached:
            user32.AttachThreadInput(current_thread, foreground_thread, False)


def _has_keyboard_focus(control) -> bool:
    try:
        return bool(control.get_properties().get("has_keyboard_focus"))
    except Exception:
        return False


def _is_codex_composer(control) -> bool:
    """Match both legacy Group and current Edit ProseMirror composers."""
    control_type = str(control.element_info.control_type or "")
    class_tokens = str(control.element_info.class_name or "").split()
    return control_type in {"Edit", "Group"} and "ProseMirror" in class_tokens


def _locate_codex_composer(preferred_hwnd: int = 0):
    if Desktop is None:
        raise RuntimeError("电脑端缺少 pywinauto，请重新安装 requirements.txt")

    windows = Desktop(backend="uia").windows()
    if preferred_hwnd:
        windows.sort(key=lambda window: 0 if int(window.handle or 0) == int(preferred_hwnd) else 1)

    foreground = int(user32.GetAncestor(user32.GetForegroundWindow(), GA_ROOT) or 0)
    matches = []
    for window in windows:
        process_path = _process_image(window.element_info.process_id)
        if not _is_codex_host(process_path):
            continue
        composers = []
        for control in window.descendants():
            rectangle = control.element_info.rectangle
            if not _is_codex_composer(control):
                continue
            if not control.element_info.visible or not control.element_info.enabled:
                continue
            if rectangle.width() < 120 or rectangle.height() < 20:
                continue
            composers.append(control)
        if composers:
            composer = max(composers, key=lambda control: control.element_info.rectangle.bottom)
            active = int(window.handle or 0) == foreground
            preferred = int(window.handle or 0) == int(preferred_hwnd or 0)
            matches.append((preferred, active, window, composer))

    if not matches:
        raise RuntimeError("没有找到 Codex 对话输入框，请确认 Codex 桌面应用已经打开")
    _, _, window, composer = max(matches, key=lambda item: (item[0], item[1]))
    return window, composer


def focus_codex_composer(preferred_hwnd: int = 0) -> dict:
    try:
        window, composer = _locate_codex_composer(preferred_hwnd)
        hwnd = int(window.handle or 0)
        _activate_window(hwnd)
        window.set_focus()
        composer.set_focus()
        for _ in range(8):
            if _has_keyboard_focus(composer):
                break
            time.sleep(0.05)
        if not _has_keyboard_focus(composer):
            # The point comes from the UIA element itself, so this remains stable
            # across window sizes and display scaling.
            composer.click_input()
            for _ in range(8):
                if _has_keyboard_focus(composer):
                    break
                time.sleep(0.05)
        if not _has_keyboard_focus(composer):
            raise RuntimeError("Codex 输入框没有获得焦点")
        return {
            "ok": True,
            "hwnd": hwnd,
            "title": window.window_text() or _window_title(hwnd) or "Codex",
            "looks_like_codex": True,
        }
    except Exception as exc:
        return {"ok": False, "hwnd": 0, "title": "", "looks_like_codex": False, "msg": str(exc)}


def capture_current_target() -> dict:
    return focus_codex_composer()


def open_new_task() -> dict:
    """Ask Codex Desktop to open exactly one blank task."""
    try:
        window, _ = _locate_codex_composer()
        hwnd = int(window.handle or 0)
        buttons = [
            control for control in window.descendants(control_type="Button")
            if str(control.window_text() or "").strip() in NEW_TASK_LABELS
            and control.is_visible()
            and control.is_enabled()
        ]
        if not buttons:
            raise RuntimeError("Codex 没有找到新建任务按钮")

        # Codex may expose a second compact button in the recent-task section.
        # The topmost button is the stable global new-task action.
        button = min(buttons, key=lambda control: control.rectangle().top)
        _activate_window(hwnd)
        button.invoke()
        return {
            "ok": True,
            "stage": "new_task_opened",
            "hwnd": hwnd,
            "title": window.window_text() or _window_title(hwnd) or "Codex",
        }
    except Exception as exc:
        return {"ok": False, "stage": "open_new_task", "msg": str(exc)}


def type_into_target(hwnd: int, text: str, append_space: bool = False) -> dict:
    value = str(text or "")
    if not value:
        return {"ok": False, "stage": "validate", "sent": 0, "msg": "没有识别到文字"}
    if len(value) > 5000:
        return {"ok": False, "stage": "validate", "sent": 0, "msg": "语音文字过长"}

    focused = focus_codex_composer(int(hwnd or 0))
    if not focused.get("ok"):
        return {
            "ok": False,
            "stage": "locate_codex",
            "sent": 0,
            "msg": focused.get("msg") or "无法聚焦 Codex 输入框",
        }

    payload = value
    if append_space and not payload[-1].isspace():
        payload += " "
    sent = keytrigger.type_text(payload)
    if sent <= 0:
        return {"ok": False, "stage": "inject_text", "sent": 0, "msg": "文字注入失败"}
    return {
        "ok": True,
        "stage": "done",
        "sent": sent,
        "chars": len(payload),
        "title": focused.get("title") or "Codex",
    }


def enter_test_phrase() -> dict:
    """Atomically locate Codex, focus its composer, and enter the fixed test phrase."""
    return type_into_target(0, CODEX_TEST_PHRASE, False)


def start_zhipu_dictation() -> dict:
    """Focus Codex and hold Right Ctrl for Zhipu AI Input."""
    focused = focus_codex_composer()
    if not focused.get("ok"):
        return {
            "ok": False,
            "stage": "locate_codex",
            "msg": focused.get("msg") or "无法聚焦 Codex 输入框",
        }
    if not keytrigger.key_down("rctrl"):
        return {"ok": False, "stage": "key_down", "msg": "右 Ctrl 按下失败"}
    return {
        "ok": True,
        "stage": "listening",
        "hwnd": int(focused.get("hwnd") or 0),
        "title": focused.get("title") or "Codex",
    }


def stop_zhipu_dictation() -> dict:
    """Release Right Ctrl so Zhipu can finish transcription."""
    if not keytrigger.key_up("rctrl"):
        return {"ok": False, "stage": "key_up", "msg": "右 Ctrl 释放失败"}
    return {"ok": True, "stage": "released"}


def submit_codex_composer(preferred_hwnd: int = 0) -> dict:
    """Focus the captured Codex composer and submit its current content."""
    focused = focus_codex_composer(int(preferred_hwnd or 0))
    if not focused.get("ok"):
        return {
            "ok": False,
            "stage": "locate_codex",
            "msg": focused.get("msg") or "无法聚焦 Codex 输入框",
        }
    if not keytrigger.simulate_key([], "enter"):
        return {"ok": False, "stage": "press_enter", "msg": "Enter 按键发送失败"}
    return {
        "ok": True,
        "stage": "submitted",
        "title": focused.get("title") or "Codex",
    }

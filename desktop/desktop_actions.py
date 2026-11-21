"""Safe desktop actions shared by the Wi-Fi and USB protocol servers."""
import ctypes
import subprocess
import time
import webbrowser
from urllib.parse import urlsplit

import app_registry


MAX_URL_LENGTH = 2048


def validate_url(value: object) -> tuple[str | None, str | None]:
    if not isinstance(value, str):
        return None, "网站地址无效"
    url = value.strip()
    if not url or len(url) > MAX_URL_LENGTH or any(ord(char) < 32 for char in url):
        return None, "网站地址无效"
    try:
        parsed = urlsplit(url)
    except ValueError:
        return None, "网站地址格式不正确"
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return None, "只支持 http 或 https 网站地址"
    if parsed.username is not None or parsed.password is not None:
        return None, "网站地址不能包含账号或密码"
    return url, None


def open_url(value: object) -> tuple[bool, str]:
    url, error = validate_url(value)
    if error:
        return False, error
    try:
        opened = webbrowser.open(url, new=2)
    except Exception as exc:
        return False, f"无法打开网站: {exc}"
    if not opened:
        return False, "Windows 未能启动默认浏览器"
    return True, ""


def read_windows_clipboard() -> tuple[str | None, str | None]:
    """Read Unicode text once after an explicit request from a paired phone."""
    if not hasattr(ctypes, "windll"):
        return None, "当前系统不支持读取 Windows 剪贴板"
    user32 = ctypes.windll.user32
    user32.OpenClipboard.argtypes = [ctypes.c_void_p]
    user32.OpenClipboard.restype = ctypes.c_bool
    user32.GetClipboardData.argtypes = [ctypes.c_uint]
    user32.GetClipboardData.restype = ctypes.c_void_p
    user32.CloseClipboard.argtypes = []
    user32.CloseClipboard.restype = ctypes.c_bool
    kernel32 = ctypes.windll.kernel32
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalUnlock.restype = ctypes.c_bool
    opened = False
    for _ in range(4):
        if user32.OpenClipboard(None):
            opened = True
            break
        time.sleep(0.03)
    if not opened:
        return None, "无法读取电脑剪贴板，请关闭正在占用剪贴板的程序后重试"
    pointer = None
    try:
        handle = user32.GetClipboardData(13)  # CF_UNICODETEXT
        if not handle:
            return None, "电脑剪贴板中没有文字"
        pointer = kernel32.GlobalLock(handle)
        if not pointer:
            return None, "无法锁定电脑剪贴板内容"
        value = ctypes.wstring_at(pointer)
        return value, None
    except Exception:
        return None, "无法读取电脑剪贴板"
    finally:
        if pointer:
            kernel32.GlobalUnlock(handle)
        user32.CloseClipboard()


def authorize_clipboard_app() -> tuple[dict | None, str | None]:
    text, error = read_windows_clipboard()
    if error:
        return None, error
    return app_registry.authorize_path(text)


def read_clipboard_url() -> tuple[str | None, str | None]:
    text, error = read_windows_clipboard()
    if error:
        return None, error
    return validate_url(text)


def is_authorized_app(app_id: object) -> bool:
    return isinstance(app_id, str) and app_registry.get_app(app_id) is not None


def launch_authorized_app(app_id: object) -> tuple[bool, str]:
    if not isinstance(app_id, str):
        return False, "尚未选择电脑上的软件"
    app = app_registry.get_app(app_id)
    if not app:
        return False, "该软件尚未授权，请重新读取电脑复制的路径"
    path, error = app_registry.normalize_executable_path(app.get("path", ""))
    if error:
        return False, error
    try:
        subprocess.Popen([path], shell=False, close_fds=True)
    except OSError as exc:
        return False, f"无法启动 {app.get('name') or '软件'}: {exc}"
    return True, ""

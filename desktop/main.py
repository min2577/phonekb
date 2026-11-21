"""main.py - 桌面端入口 (V2)。"""
import sys
import os
# frozen (PyInstaller) æ¶æ LOG_DIR æå° exe åç®å½ï¼å¦åç¨æºç ç®å½
if getattr(sys, "frozen", False):
    LOG_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    LOG_DIR = os.path.dirname(os.path.abspath(__file__))
def _setup_log():
    log_file = os.path.join(LOG_DIR, "main.log")
    try:
        log_fd = os.open(log_file, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        os.dup2(log_fd, 1)
        os.dup2(log_fd, 2)
        os.close(log_fd)
        sys.stdout = open(1, "w", buffering=1, encoding="utf-8", closefd=False)
        sys.stderr = open(2, "w", buffering=1, encoding="utf-8", closefd=False)
    except Exception:
        pass
_setup_log()

import asyncio
import ctypes
import logging
import socket as _sock
import threading
import time
import webbrowser

import pystray
from PIL import Image, ImageDraw

import pairing
import server
import usb_server
import adb_tunnel
import spp_bridge
import gamepad_editor_server
from main_window import MainWindow
from PySide6 import QtCore

user32 = ctypes.WinDLL("user32", use_last_error=True)
try:
    user32.LockSetForegroundWindow(2)
    user32.AllowSetForegroundWindow(0xFFFFFFFF)
except Exception:
    pass

log = logging.getLogger("phonekb.main")


class _UiBridge(QtCore.QObject):
    """将托盘线程/重复启动请求安全地转发到 Qt 主线程。"""

    show_pairing = QtCore.Signal()
    show_editor = QtCore.Signal()


def _activate_existing_window() -> bool:
    """尝试恢复已隐藏的 PhoneKB 窗口，返回是否找到窗口。"""
    try:
        found = {"value": False}
        enum_windows = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        get_title = user32.GetWindowTextW
        get_title.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
        get_title.restype = ctypes.c_int

        @enum_windows
        def callback(hwnd, _lparam):
            title_buf = ctypes.create_unicode_buffer(256)
            if get_title(hwnd, title_buf, len(title_buf)) and title_buf.value.startswith("PhoneKB"):
                found["value"] = True
                user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                user32.SetForegroundWindow(hwnd)
                return False
            return True

        user32.EnumWindows(callback, 0)
        return found["value"]
    except Exception as exc:
        print(f"[main] 唤醒已有窗口失败: {exc}", flush=True)
        return False


def _check_single_instance() -> bool:
    for port in (9876, 9877, 9878):
        s = _sock.socket(_sock.AF_INET, _sock.SOCK_STREAM)
        s.setsockopt(_sock.SOL_SOCKET, _sock.SO_REUSEADDR, 1)
        try:
            s.bind(("0.0.0.0", port))
            s.close()
        except OSError as e:
            s.close()
            print(f"[main] 端口 {port} 已被占用: {e}", flush=True)
            return False
    return True


def _show_instance_conflict() -> None:
    message = (
        "PhoneKB 无法启动，因为旧版本仍在后台运行。\n\n"
        "请先退出右下角系统托盘中的旧版 PhoneKB，"
        "再双击桌面的 PhoneKB 图标。"
    )
    try:
        user32.MessageBoxW(None, message, "PhoneKB 启动失败", 0x00010030)
    except Exception:
        time.sleep(3)


def _make_tray_icon() -> Image.Image:
    img = Image.new("RGB", (64, 64), (0, 102, 204))
    draw = ImageDraw.Draw(img)
    draw.rectangle((18, 12, 24, 52), fill="white")
    draw.polygon([(24, 32), (44, 12), (50, 12), (30, 32)], fill="white")
    draw.polygon([(24, 32), (44, 52), (50, 52), (30, 32)], fill="white")
    return img


class App:
    def __init__(self):
        self.info = pairing.create_pairing()
        server.configure(self.info["code"], self.info["secret"], self.info["port"])
        server.load_data()
        log.info(f"配对码: {self.info['code']}  IP: {self.info['lan_ip']}:{self.info['port']}")

        self._main_window_ref = None
        self.tray_icon: pystray.Icon = self._build_tray()
        self.tray_thread = threading.Thread(target=self.tray_icon.run, name="tray", daemon=True)
        self._shutdown_event = threading.Event()
        self._server_thread = None
        self._usb_server_thread = None
        self._gamepad_editor_thread = None
        self._adb_monitor = adb_tunnel.AdbReverseMonitor()
        self._ui_bridge = _UiBridge()

    def _build_tray(self) -> pystray.Icon:
        code = self.info["code"]

        def show_pairing_window(icon, item):
            mw = getattr(self, "_main_window_ref", None)
            if mw is None:
                log.info("show_pairing_window: mw is None, skip")
                return
            self._ui_bridge.show_pairing.emit()

        def quit_app(icon, item):
            log.info("退出")
            icon.stop()
            self._shutdown_event.set()

        def copy_code(icon, item):
            try:
                import pyperclip
                pyperclip.copy(code)
            except Exception:
                pass

        def reset_pairing(icon, item):
            try:
                new_info = self.regenerate_pairing()
                icon.notify("已重新生成", "新配对码: " + new_info["code"] + "  窗口中也会同步")
            except Exception as e:
                icon.notify("重置失败", str(e)[:60])

        def export_logs(icon, item):
            try:
                import shutil
                ts = time.strftime("%Y%m%d_%H%M%S")
                out = os.path.join(LOG_DIR, f"phonekb_logs_{ts}.zip")
                with __import__("zipfile").ZipFile(out, "w") as z:
                    for fn in ("main.log", "server.log", "gui.log"):
                        p = os.path.join(LOG_DIR, fn)
                        if os.path.exists(p):
                            z.write(p, fn)
                icon.notify("日志已导出", out)
            except Exception as e:
                icon.notify("导出失败", str(e))

        def show_devices(icon, item):
            n = len(server._sessions)
            icon.notify(f"{n} 台设备在线", ", ".join(m.get("ip", "?") for m in server._sessions.values())[:80])

        def open_gamepad_editor(icon, item):
            mw = getattr(self, "_main_window_ref", None)
            if mw is None:
                icon.notify("主窗口未就绪", "请稍后再试")
                return
            self._ui_bridge.show_editor.emit()

        return pystray.Icon(
            "phonekb",
            _make_tray_icon(),
            title=f"手机键盘  配对码: {code}",
            menu=pystray.Menu(
                pystray.MenuItem("显示配对码 / 二维码", show_pairing_window, default=True),
                pystray.MenuItem(f"配对码：{code}", None, enabled=False),
                pystray.MenuItem("复制配对码", copy_code),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("打开手柄布局编辑器", open_gamepad_editor),
                pystray.MenuItem("当前连接设备", show_devices),
                pystray.MenuItem("导出日志", export_logs),
                pystray.MenuItem("重置配对", reset_pairing),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("退出", quit_app),
            ),
        )

    def _start_server_thread(self):
        server.SECRET_CODE = self.info["code"]
        server.SECRET_FULL = self.info["secret"]
        server.PORT = self.info["port"]

        def _run_ws():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(server.run())
            except Exception as e:
                log.exception(f"ws server 线程异常: {e}")
            finally:
                loop.close()

        def _run_usb():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(usb_server.run())
            except Exception as e:
                log.exception(f"usb server 线程异常: {e}")
            finally:
                loop.close()

        def _run_spp():
            try:
                spp_bridge.run_spp_server()
            except Exception as e:
                log.exception(f"spp bridge 异常: {e}")

        def _run_gamepad_editor():
            try:
                gamepad_editor_server.run()
            except Exception as e:
                log.exception(f"手柄布局编辑器服务异常: {e}")

        self._server_thread = threading.Thread(target=_run_ws, name="wsserver", daemon=True)
        self._server_thread.start()
        self._usb_server_thread = threading.Thread(target=_run_usb, name="usbserver", daemon=True)
        self._usb_server_thread.start()
        self._adb_monitor.start()
        self._spp_server_thread = threading.Thread(target=_run_spp, name="sppserver", daemon=True)
        self._spp_server_thread.start()
        self._gamepad_editor_thread = threading.Thread(target=_run_gamepad_editor, name="gamepad-editor", daemon=True)
        self._gamepad_editor_thread.start()

    def regenerate_pairing(self):
        """删旧 pairing.json + 算新 code/secret + 同步 server + 通知窗口。返回新 info。"""
        try:
            os.remove(pairing._PAIRING_FILE)
        except OSError:
            pass
        new_info = pairing.create_pairing()
        import server
        server.configure(new_info["code"], new_info["secret"], new_info["port"])
        self.info = new_info
        log.info("重新生成配对码: %s  IP: %s:%s" % (new_info["code"], new_info["lan_ip"], new_info["port"]))
        if getattr(self, "_main_window_ref", None) is not None:
            try:
                self._main_window_ref.update_pairing_info(new_info)
            except Exception as e:
                log.exception(f"notify window: {e}")
        return new_info

    def run(self):
        def _on_phone_paired(ws=None):
            log.info(f"手机上线，当前连接: {len(server._sessions)}")
        server.on_pair(_on_phone_paired)

        self._start_server_thread()
        self.tray_thread.start()

        log.info("构建并显示主窗口…")
        from PySide6 import QtWidgets as _QtWidgets
        qt_app = _QtWidgets.QApplication.instance() or _QtWidgets.QApplication(sys.argv)
        qt_app.setQuitOnLastWindowClosed(False)  # 关窗不退出，由托盘退出触发
        mw = MainWindow(self.info, on_regenerate=self.regenerate_pairing)
        self._main_window_ref = mw
        self._ui_bridge.show_pairing.connect(mw.show_pairing_page, QtCore.Qt.QueuedConnection)
        self._ui_bridge.show_editor.connect(mw.show_editor_page, QtCore.Qt.QueuedConnection)
        mw.show_pairing_page()

        def _check_shutdown():
            if self._shutdown_event.is_set():
                log.info("shutdown 已请求, quit mainloop")
                try:
                    mw.close()
                    qt_app.quit()
                except Exception:
                    pass
            else:
                try:
                    QtCore.QTimer.singleShot(200, _check_shutdown)
                except Exception:
                    pass
        QtCore.QTimer.singleShot(200, _check_shutdown)

        log.info("就绪。主窗口已显示，关闭后最小化到系统托盘。")
        qt_app.exec()
        log.info("主进程退出")


def _archive_stale_server_log():
    try:
        server_log = os.path.join(LOG_DIR, "server.log")
        if os.path.exists(server_log):
            import time as _t
            bak = server_log + f".{int(_t.time())}.bak"
            os.rename(server_log, bak)
            print("[main] 归档旧 server.log -> " + os.path.basename(bak), flush=True)
    except Exception as e:
        print("[main] server.log 归档失败: " + str(e), flush=True)

def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
        sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)
    except Exception:
        pass
    _archive_stale_server_log()
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("phonekb").setLevel(logging.INFO)
    if not _check_single_instance():
        # 已有实例通常只是隐藏在托盘；双击启动应直接恢复它。
        for _ in range(10):
            if _activate_existing_window():
                return
            time.sleep(0.2)
        print("[main] 检测到端口已被占用，显示冲突提示后退出。", flush=True)
        _show_instance_conflict()
        sys.exit(1)
    App().run()


if __name__ == "__main__":
    main()

"""Detect and resolve one visible Codex Desktop approval prompt via UIA."""

from __future__ import annotations

import hashlib
import threading
import time
from typing import Callable, Iterable, Optional

import codex_voice


ALLOW_LABELS = {"允许一次", "allow once"}
REJECT_LABELS = {"拒绝", "reject"}


def _normalized_label(value: object) -> str:
    return " ".join(str(value or "").strip().split()).casefold()


def _element_label(control) -> str:
    try:
        return _normalized_label(control.window_text())
    except Exception:
        return ""


def _usable(control) -> bool:
    try:
        info = control.element_info
        return bool(info.visible and info.enabled)
    except Exception:
        return False


def _element_identity(control) -> str:
    try:
        info = control.element_info
        rectangle = info.rectangle
        return "|".join([
            str(getattr(info, "automation_id", "") or ""),
            str(getattr(info, "control_id", "") or ""),
            str(getattr(info, "process_id", "") or ""),
            str(rectangle.left),
            str(rectangle.top),
            str(rectangle.right),
            str(rectangle.bottom),
            _element_label(control),
        ])
    except Exception:
        return _element_label(control)


def _codex_windows() -> list:
    if codex_voice.Desktop is None:
        raise RuntimeError("电脑端缺少 pywinauto，请重新安装 requirements.txt")
    matches = []
    for window in codex_voice.Desktop(backend="uia").windows():
        try:
            process_path = codex_voice._process_image(window.element_info.process_id)  # type: ignore[attr-defined]
            if codex_voice._is_codex_host(process_path):  # type: ignore[attr-defined]
                matches.append(window)
        except Exception:
            continue
    return matches


class CodexApprovalController:
    def __init__(self, window_provider: Optional[Callable[[], Iterable]] = None):
        self._window_provider = window_provider or _codex_windows
        self._lock = threading.RLock()

    def scan(self) -> dict:
        with self._lock:
            try:
                groups = self._find_groups()
            except Exception as exc:
                return {
                    "pending": False,
                    "ambiguous": False,
                    "fingerprint": "",
                    "msg": "无法检查 Codex 审批界面: " + str(exc),
                }
            if not groups:
                return {"pending": False, "ambiguous": False, "fingerprint": "", "msg": ""}
            if len(groups) != 1 or groups[0].get("invalid"):
                return {
                    "pending": False,
                    "ambiguous": True,
                    "fingerprint": "",
                    "msg": "检测到多个审批目标，请在电脑端只保留一个待处理请求",
                }
            return self._public_status(groups[0])

    def resolve(self, decision: str, fingerprint: str) -> dict:
        action = "approve" if decision == "approve" else "reject"
        with self._lock:
            groups = self._find_groups()
            if not groups:
                return {"ok": False, "msg": "当前没有待批准请求"}
            if len(groups) != 1 or groups[0].get("invalid"):
                return {"ok": False, "msg": "检测到多个审批目标，已取消操作"}
            group = groups[0]
            current = self._public_status(group)
            if not fingerprint or current["fingerprint"] != str(fingerprint):
                return {"ok": False, "msg": "审批请求已经变化，请刷新后重试"}

            window = group["window"]
            target = group[action]
            try:
                hwnd = int(window.handle or 0)
                codex_voice._activate_window(hwnd)  # type: ignore[attr-defined]
                window.set_focus()
                self._invoke(target)
            except Exception as exc:
                return {"ok": False, "msg": "无法点击 Codex 审批按钮: " + str(exc)}

            for _ in range(15):
                time.sleep(0.1)
                next_groups = self._find_groups()
                if not next_groups:
                    return {"ok": True, "msg": "已允许一次" if action == "approve" else "已拒绝"}
                valid_groups = [item for item in next_groups if not item.get("invalid")]
                if len(valid_groups) == 1 and self._public_status(valid_groups[0])["fingerprint"] != current["fingerprint"]:
                    return {"ok": True, "msg": "已允许一次" if action == "approve" else "已拒绝"}
            return {"ok": False, "msg": "已点击按钮，但 Codex 审批卡片没有消失"}

    def _find_groups(self) -> list[dict]:
        groups = []
        for window in list(self._window_provider()):
            allows = []
            rejects = []
            try:
                buttons = window.descendants(control_type="Button")
            except Exception:
                continue
            for control in buttons:
                if not _usable(control):
                    continue
                label = _element_label(control)
                if label in ALLOW_LABELS:
                    allows.append(control)
                elif label in REJECT_LABELS:
                    rejects.append(control)
            if len(allows) == 1 and len(rejects) == 1:
                groups.append({"window": window, "approve": allows[0], "reject": rejects[0]})
            elif allows or rejects:
                # A partial or duplicated button set is intentionally ambiguous.
                groups.append({"window": window, "approve": None, "reject": None, "invalid": True})
        return groups

    @staticmethod
    def _public_status(group: dict) -> dict:
        window = group["window"]
        approve = group["approve"]
        reject = group["reject"]
        hwnd = int(getattr(window, "handle", 0) or 0)
        raw = str(hwnd) + "|" + _element_identity(approve) + "|" + _element_identity(reject)
        fingerprint = hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()[:20]
        return {
            "pending": True,
            "ambiguous": False,
            "fingerprint": fingerprint,
            "hwnd": hwnd,
            "msg": "Codex 正在等待批准终端操作",
        }

    @staticmethod
    def _invoke(control) -> None:
        try:
            control.invoke()
            return
        except Exception:
            pass
        try:
            control.iface_invoke.Invoke()
            return
        except Exception:
            pass
        control.click_input()

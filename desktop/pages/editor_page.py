"""Single-layer visual control editor for PhoneKB."""
from __future__ import annotations

import copy
import json
import logging
import os
import random

from PySide6 import QtCore, QtGui, QtWidgets

import gamepad_layouts_loader

try:
    import layouts_loader
except Exception:  # Built packages without the shortcut preset directory still work.
    layouts_loader = None


log = logging.getLogger("phonekb.editor_page")

TYPE_INFO = {
    "leftStick": {"title": "移动摇杆", "icon": "WASD", "mode": "四方向组件", "label": "移动", "slots": ["up", "left", "down", "right"]},
    "rightStick": {"title": "视角摇杆", "icon": "+", "mode": "鼠标视角", "label": "视角", "slots": []},
    "dpad": {"title": "十字方向键", "icon": "十", "mode": "四方向组件", "label": "方向键", "slots": ["up", "left", "down", "right"]},
    "abxy": {"title": "ABXY 按键组", "icon": "AB", "mode": "四个独立按键", "label": "ABXY", "slots": ["a", "b", "x", "y"]},
    "shoulder": {"title": "肩键 / 扳机", "icon": "L/R", "mode": "单键或组合键", "label": "肩键", "slots": ["press"]},
    "key": {"title": "自定义按键", "icon": "K", "mode": "单键或组合键", "label": "按键", "slots": ["press"]},
    "mouse": {"title": "鼠标区域", "icon": "M", "mode": "鼠标视角", "label": "鼠标", "slots": []},
    "macro": {"title": "快捷键按钮", "icon": "⌘", "mode": "组合快捷键", "label": "快捷键", "slots": ["press"]},
}
COMPONENT_TYPES = list(TYPE_INFO)
SLOT_LABELS = {
    "up": "上方向", "left": "左方向", "down": "下方向", "right": "右方向",
    "a": "A 按钮", "b": "B 按钮", "x": "X 按钮", "y": "Y 按钮", "press": "按下时",
}
BACKGROUND_PRESETS = {
    "mobile-light": {
        "title": "手机浅色", "subtitle": "默认手机方案", "kind": "mobile-light",
        "stage_top": "#f9fdff", "stage_bottom": "#dff0f8", "grid": "#83aabd",
        "button_top": "#58a8ff", "button_bottom": "#286cda", "button_border": "#dff5ff", "button_text": "#ffffff",
        "control_fill": "#dff7f5", "control_border": "#49bbb2", "control_inner": "#eef9fc", "accent": "#18a899",
    },
    "mobile-dark": {
        "title": "手机暗色", "subtitle": "低亮度方案", "kind": "mobile",
        "stage_top": "#1e2536", "stage_bottom": "#0f1320", "grid": "#ffffff",
        "button_top": "#2a3142", "button_bottom": "#1a1f2c", "button_border": "#94a3b8", "button_text": "#dce7eb",
        "control_fill": "#1a1f2c", "control_border": "#94a3b8", "control_inner": "#475569", "accent": "#38bdf8",
    },
    "terrain": {
        "title": "山野道路", "subtitle": "场景化背景", "kind": "terrain",
        "stage_top": "#2b7089", "stage_bottom": "#347457", "grid": "#23404c",
        "button_top": "#438cf6", "button_bottom": "#1c5acb", "button_border": "#b9ddff", "button_text": "#ffffff",
        "control_fill": "#155396", "control_border": "#79baff", "control_inner": "#58b7ff", "accent": "#48ded3",
    },
    "arcade-neon": {
        "title": "街机霓虹", "subtitle": "高对比街机", "kind": "arcade",
        "stage_top": "#251735", "stage_bottom": "#101d2d", "grid": "#d66dff",
        "button_top": "#4b2760", "button_bottom": "#221634", "button_border": "#e277ff", "button_text": "#fbeaff",
        "control_fill": "#321e50", "control_border": "#e277ff", "control_inner": "#71368f", "accent": "#ff6bc7",
    },
    "paper-grid": {
        "title": "纸面网格", "subtitle": "浅色工作台", "kind": "paper",
        "stage_top": "#f4f8f9", "stage_bottom": "#e1ebee", "grid": "#78909c",
        "button_top": "#ffffff", "button_bottom": "#d9e4ea", "button_border": "#6f8791", "button_text": "#20323a",
        "control_fill": "#d8e7eb", "control_border": "#5f8c9d", "control_inner": "#a9c9d3", "accent": "#0d9296",
    },
}
CANVAS_PRESETS = [("手机横屏 20:9", 2400, 1080), ("宽屏 16:9", 1920, 1080), ("平板 4:3", 1600, 1200)]
REFERENCE_PHONE_WIDTH = 1080.0
MIN_CONTROL_SIZE = 50
INITIAL_SIZE_SLIDER_MAX = 400
MODIFIER_LABELS = {"ctrl": "Ctrl", "shift": "Shift", "alt": "Alt", "win": "Win"}
KEY_ALIASES = {
    "space": "Space", "esc": "Esc", "enter": "Enter", "tab": "Tab", "backspace": "Backspace",
    "up": "↑", "down": "↓", "left": "←", "right": "→", "ctrl": "Ctrl", "shift": "Shift",
    "alt": "Alt", "win": "Win", "home": "Home", "delete": "Delete",
}
COMMON_KEYS = ["W", "A", "S", "D", "J", "K", "U", "I", "Space", "Enter", "Tab", "Esc", "Backspace", "↑", "↓", "←", "→", "Home", "F1", "F2", "F12"]

EDITOR_STYLE = """
QWidget#desktopGamepadEditor { background: #dce6e9; color: #1b292f; font-family: "Microsoft YaHei UI", "Microsoft YaHei"; }
QToolTip { color: #eef7f8; background: #263a42; border: 1px solid #415a64; padding: 5px; }
QPushButton, QToolButton { letter-spacing: 0px; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 0; }
QScrollBar::handle:vertical { background: #b5c5ca; min-height: 28px; border-radius: 4px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""


def _uid(prefix="c"):
    return f"{prefix}_{random.randint(0, 0xFFFFFF):06x}"


def _clamp(value, low, high):
    return max(low, min(high, value))


def _key_display(value):
    value = str(value or "").strip()
    return KEY_ALIASES.get(value.lower(), value.upper() if len(value) == 1 else value) or "未设置"


def _binding_display(binding):
    if not isinstance(binding, dict) or not binding.get("key"):
        return "未设置"
    parts = [MODIFIER_LABELS.get(str(value).lower(), str(value)) for value in binding.get("modifiers") or []]
    parts.append(_key_display(binding.get("key")))
    return " + ".join(parts)


def _binding_compact(binding, limit=7):
    value = _binding_display(binding)
    return value if len(value) <= limit else value[:limit - 1] + "…"


def _qt_key_name(key):
    mapping = {
        int(QtCore.Qt.Key_Space): "space", int(QtCore.Qt.Key_Escape): "esc",
        int(QtCore.Qt.Key_Return): "enter", int(QtCore.Qt.Key_Enter): "enter",
        int(QtCore.Qt.Key_Tab): "tab", int(QtCore.Qt.Key_Backspace): "backspace",
        int(QtCore.Qt.Key_Up): "up", int(QtCore.Qt.Key_Down): "down",
        int(QtCore.Qt.Key_Left): "left", int(QtCore.Qt.Key_Right): "right",
        int(QtCore.Qt.Key_Delete): "delete", int(QtCore.Qt.Key_Home): "home",
        int(QtCore.Qt.Key_Control): "ctrl", int(QtCore.Qt.Key_Shift): "shift", int(QtCore.Qt.Key_Alt): "alt",
    }
    value = mapping.get(int(key))
    if value:
        return value
    if int(QtCore.Qt.Key_F1) <= int(key) <= int(QtCore.Qt.Key_F35):
        return "f" + str(int(key) - int(QtCore.Qt.Key_F1) + 1)
    return ""


def _shortcut_actions():
    actions = []
    if layouts_loader is None:
        return actions
    try:
        presets = layouts_loader.load_presets()
    except Exception:
        log.exception("load shortcut presets failed")
        return actions
    for preset in presets:
        preset_name = str(preset.get("name") or "快捷键")
        for page in preset.get("pages") or []:
            for slot in page.get("slots") or []:
                key = slot.get("key") if isinstance(slot, dict) else None
                if not isinstance(key, dict) or key.get("type") != "shortcut":
                    continue
                shortcut = key.get("shortcut") if isinstance(key.get("shortcut"), dict) else {}
                binding = gamepad_layouts_loader._normalize_binding(shortcut)
                if binding:
                    actions.append({"group": preset_name, "label": str(key.get("label") or "快捷键"), "binding": binding})
    return actions


def _theme_for_background(background, custom_presets=None):
    background = background if isinstance(background, dict) else {"id": str(background or "mobile-light")}
    background_id = str(background.get("id") or "mobile-light")
    base_id = str(background.get("baseId") or background_id)
    theme = dict(BACKGROUND_PRESETS.get(base_id, BACKGROUND_PRESETS["mobile-light"]))
    for preset in custom_presets or []:
        if preset.get("id") == background_id:
            theme.update(BACKGROUND_PRESETS.get(str(preset.get("baseId") or "mobile-light"), {}))
            theme.update(preset.get("theme") or {})
            theme["title"] = preset.get("name") or theme.get("title")
            theme["kind"] = preset.get("kind") or theme.get("kind")
            break
    theme.update(background.get("theme") or {})
    if background.get("kind"):
        theme["kind"] = background["kind"]
    return theme


def _clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        child = item.layout()
        if widget:
            widget.deleteLater()
        elif child:
            _clear_layout(child)


class ControlItem(QtWidgets.QWidget):
    clicked = QtCore.Signal(str)
    drag_started = QtCore.Signal()
    drag_finished = QtCore.Signal()

    def __init__(self, control, parent=None):
        super().__init__(parent)
        self._control = control
        self._selected = False
        self._dragging = False
        self._press_global = QtCore.QPointF()
        self._start_item = QtCore.QPointF()
        self._scene_scale = 1.0
        self._theme = BACKGROUND_PRESETS["mobile-light"]
        self._visual_opacity = 1.0
        self.setCursor(QtCore.Qt.OpenHandCursor)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

    def set_selected(self, selected):
        self._selected = bool(selected)
        self.update()

    def set_scene_scale(self, value):
        self._scene_scale = max(.01, float(value))
        self.update()

    def set_visual_theme(self, theme):
        self._theme = theme or BACKGROUND_PRESETS["mobile-light"]
        self.update()

    def set_visual_opacity(self, value):
        self._visual_opacity = _clamp(float(value), 0.0, 1.0)
        self.update()

    def mousePressEvent(self, event):
        if event.button() != QtCore.Qt.LeftButton:
            super().mousePressEvent(event)
            return
        self.clicked.emit(str(self._control.get("id") or ""))
        if self._control.get("locked"):
            return
        self._dragging = True
        self._press_global = event.globalPosition()
        self._start_item = QtCore.QPointF(float(self._control.get("x", 50)), float(self._control.get("y", 50)))
        self.setCursor(QtCore.Qt.ClosedHandCursor)
        self.raise_()
        self.drag_started.emit()
        event.accept()

    def mouseMoveEvent(self, event):
        if not self._dragging:
            super().mouseMoveEvent(event)
            return
        canvas = self.parentWidget()
        if canvas and hasattr(canvas, "position_from_drag"):
            delta = event.globalPosition() - self._press_global
            x, y = canvas.position_from_drag(self._start_item, delta, self.width())
            self._control["x"], self._control["y"] = round(x, 3), round(y, 3)
            canvas.update_control_position(self._control)
        event.accept()

    def mouseReleaseEvent(self, event):
        if self._dragging:
            self._dragging = False
            self.setCursor(QtCore.Qt.OpenHandCursor)
            self.drag_finished.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _binding(self, slot):
        return _binding_compact((self._control.get("bindings") or {}).get(slot), 8)

    def _appearance_color(self, field, theme_field):
        appearance = self._control.get("appearance") if isinstance(self._control.get("appearance"), dict) else {}
        return QtGui.QColor(appearance.get(field) or self._theme[theme_field])

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setOpacity(self._visual_opacity)
        painter.scale(self._scene_scale, self._scene_scale)
        w, h = self.width() / self._scene_scale, self.height() / self._scene_scale
        cx, cy = w / 2, h / 2
        ctype = self._control.get("type", "key")
        if ctype in {"key", "shoulder", "macro"}:
            self._paint_button(painter, cx, cy, w, h)
        elif ctype == "leftStick":
            self._paint_stick(painter, cx, cy, min(w, h))
        elif ctype == "rightStick":
            self._paint_reticle(painter, cx, cy, min(w, h))
        elif ctype == "dpad":
            self._paint_dpad(painter, cx, cy, min(w, h))
        elif ctype == "abxy":
            self._paint_abxy(painter, cx, cy, min(w, h))
        elif ctype == "mouse":
            self._paint_mouse(painter, cx, cy, min(w, h))
        if self._selected:
            self._paint_selection(painter, w, h, ctype)

    def _paint_selection(self, painter, w, h, ctype):
        color = QtGui.QColor("#1ba9a4")
        glow = QtGui.QColor(27, 169, 164, 45)
        rect = QtCore.QRectF(4, 4, w - 8, h - 8)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.setPen(QtGui.QPen(glow, 7))
        painter.drawRoundedRect(rect, min(18, w * .15), min(18, h * .15))
        painter.setPen(QtGui.QPen(color, 1.4))
        painter.drawRoundedRect(rect, min(18, w * .15), min(18, h * .15))
        painter.setBrush(QtGui.QColor("#ffffff"))
        painter.setPen(QtGui.QPen(QtGui.QColor("#087975"), 1))
        for point in (rect.topLeft(), rect.topRight(), rect.bottomLeft(), rect.bottomRight()):
            painter.drawRect(QtCore.QRectF(point.x() - 3, point.y() - 3, 6, 6))

    def _paint_button(self, painter, cx, cy, w, h):
        appearance = self._control.get("appearance") if isinstance(self._control.get("appearance"), dict) else {}
        shape = appearance.get("shape", "pill")
        wide = self._control.get("variant") == "wide" or self._control.get("type") in {"shoulder", "macro"}
        rect_w = min(w - 12, 108 if wide else 64)
        rect_h = min(h - 16, 44 if wide else 60)
        rect = QtCore.QRectF(cx - rect_w / 2, cy - rect_h / 2, rect_w, rect_h)
        fill = self._appearance_color("fill", "button_top")
        bottom = fill.darker(122) if appearance.get("fill") else QtGui.QColor(self._theme["button_bottom"])
        gradient = QtGui.QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0, fill)
        gradient.setColorAt(1, bottom)
        painter.setBrush(QtGui.QColor(34, 75, 91, 35))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(rect.translated(0, 4), 10, 10)
        painter.setBrush(gradient)
        painter.setPen(QtGui.QPen(self._appearance_color("border", "button_border"), 1.4))
        if shape == "diamond":
            path = QtGui.QPainterPath()
            path.moveTo(cx, rect.top())
            path.lineTo(rect.right(), cy)
            path.lineTo(cx, rect.bottom())
            path.lineTo(rect.left(), cy)
            path.closeSubpath()
            painter.drawPath(path)
        else:
            radius = rect_h / 2 if shape in {"round", "pill"} else 5
            painter.drawRoundedRect(rect, radius, radius)
        painter.setPen(self._appearance_color("text", "button_text"))
        font = painter.font()
        font.setBold(True)
        font.setPointSizeF(10 if wide else 9)
        painter.setFont(font)
        painter.drawText(rect.adjusted(3, 5, -3, -13), QtCore.Qt.AlignCenter, str(self._control.get("label") or "KEY"))
        font.setBold(False)
        font.setPointSizeF(6.8)
        painter.setFont(font)
        painter.drawText(rect.adjusted(3, rect_h * .54, -3, -3), QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop, self._binding("press"))

    def _paint_stick(self, painter, cx, cy, size):
        outer = size * .39
        fill = self._appearance_color("fill", "control_fill")
        border = self._appearance_color("border", "control_border")
        text = self._appearance_color("text", "button_text")
        painter.setBrush(QtGui.QColor(fill.red(), fill.green(), fill.blue(), 115))
        painter.setPen(QtGui.QPen(border, 2.5))
        painter.drawEllipse(QtCore.QPointF(cx, cy), outer, outer)
        painter.setPen(QtGui.QPen(QtGui.QColor(border.red(), border.green(), border.blue(), 90), 1))
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawEllipse(QtCore.QPointF(cx, cy), outer * .27, outer * .27)

        painter.setPen(QtGui.QPen(QtGui.QColor(border.red(), border.green(), border.blue(), 185), max(2, outer * .045), QtCore.Qt.SolidLine, QtCore.Qt.RoundCap))
        tick_start, tick_end = outer * .72, outer * .84
        painter.drawLine(cx, cy - tick_start, cx, cy - tick_end)
        painter.drawLine(cx, cy + tick_start, cx, cy + tick_end)
        painter.drawLine(cx - tick_start, cy, cx - tick_end, cy)
        painter.drawLine(cx + tick_start, cy, cx + tick_end, cy)

        thumb_radius = outer * .42
        button_fill = self._appearance_color("fill", "button_top")
        appearance = self._control.get("appearance") if isinstance(self._control.get("appearance"), dict) else {}
        gradient = QtGui.QLinearGradient(cx - thumb_radius, cy - thumb_radius, cx + thumb_radius, cy + thumb_radius)
        gradient.setColorAt(0, button_fill.lighter(112))
        gradient.setColorAt(1, button_fill.darker(122) if appearance.get("fill") else QtGui.QColor(self._theme["button_bottom"]))
        painter.setBrush(QtGui.QColor(26, 62, 91, 45)); painter.setPen(QtCore.Qt.NoPen)
        painter.drawEllipse(QtCore.QPointF(cx, cy + outer * .055), thumb_radius, thumb_radius)
        painter.setBrush(gradient)
        painter.setPen(QtGui.QPen(self._appearance_color("border", "button_border"), 1.5))
        painter.drawEllipse(QtCore.QPointF(cx, cy), thumb_radius, thumb_radius)
        painter.setBrush(QtGui.QColor(255, 255, 255, 35))
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 90), 1))
        painter.drawEllipse(QtCore.QPointF(cx, cy), thumb_radius * .28, thumb_radius * .28)

        painter.setPen(text)
        font = painter.font(); font.setBold(True); font.setPointSizeF(6.5); painter.setFont(font)
        binding_text = "/".join(self._binding(slot) for slot in ("up", "left", "down", "right"))
        painter.drawText(QtCore.QRectF(cx - outer * .67, cy + outer * .5, outer * 1.34, 13), QtCore.Qt.AlignCenter, binding_text)
        self._paint_caption(painter, cx, cy + outer + 8, str(self._control.get("label") or "移动"))

    def _paint_reticle(self, painter, cx, cy, size):
        outer = size * .4
        fill = self._appearance_color("fill", "control_fill")
        border = self._appearance_color("border", "control_border")
        accent = QtGui.QColor(self._theme["accent"])
        painter.setBrush(QtGui.QColor(fill.red(), fill.green(), fill.blue(), 100))
        painter.setPen(QtGui.QPen(border, 3))
        painter.drawEllipse(QtCore.QPointF(cx, cy), outer, outer)
        painter.setBrush(QtGui.QColor(255, 255, 255, 90))
        painter.setPen(QtGui.QPen(accent, 2))
        painter.drawEllipse(QtCore.QPointF(cx, cy), outer * .24, outer * .24)
        painter.drawLine(cx - outer * .14, cy, cx + outer * .14, cy)
        painter.drawLine(cx, cy - outer * .14, cx, cy + outer * .14)
        self._paint_caption(painter, cx, cy + outer + 7, str(self._control.get("label") or "视角"))

    def _paint_dpad(self, painter, cx, cy, size):
        d = size * .23
        fill = self._appearance_color("fill", "button_top")
        appearance = self._control.get("appearance") if isinstance(self._control.get("appearance"), dict) else {}
        bottom = fill.darker(122) if appearance.get("fill") else QtGui.QColor(self._theme["button_bottom"])
        gradient = QtGui.QLinearGradient(cx - d, cy - d, cx + d, cy + d)
        gradient.setColorAt(0, fill); gradient.setColorAt(1, bottom)
        painter.setBrush(gradient)
        painter.setPen(QtGui.QPen(self._appearance_color("border", "button_border"), 1.4))
        painter.drawRoundedRect(QtCore.QRectF(cx - d * .52, cy - d * 1.45, d * 1.04, d * 2.9), 6, 6)
        painter.drawRoundedRect(QtCore.QRectF(cx - d * 1.45, cy - d * .52, d * 2.9, d * 1.04), 6, 6)
        painter.setPen(self._appearance_color("text", "button_text"))
        font = painter.font(); font.setBold(True); font.setPointSizeF(6.5); painter.setFont(font)
        for slot, rect in {
            "up": (cx - 20, cy - d * 1.3, 40, 15), "down": (cx - 20, cy + d * .8, 40, 15),
            "left": (cx - d * 1.35, cy - 8, 36, 16), "right": (cx + d * .35, cy - 8, 36, 16),
        }.items():
            painter.drawText(QtCore.QRectF(*rect), QtCore.Qt.AlignCenter, self._binding(slot))

    def _paint_abxy(self, painter, cx, cy, size):
        d = size * .25
        appearance = self._control.get("appearance") if isinstance(self._control.get("appearance"), dict) else {}
        semantic = {"y": "#f7c447", "x": "#5599ed", "a": "#42c783", "b": "#ef6f7b"}
        for slot, dx, dy, label in [("y", 0, -d, "Y"), ("x", -d, 0, "X"), ("a", d, 0, "A"), ("b", 0, d, "B")]:
            center = QtCore.QPointF(cx + dx, cy + dy)
            radius = size * .145
            painter.setBrush(QtGui.QColor(35, 70, 90, 35))
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawEllipse(center + QtCore.QPointF(0, 3), radius, radius)
            fill = QtGui.QColor(appearance.get("fill") or semantic[slot])
            gradient = QtGui.QLinearGradient(center.x() - radius, center.y() - radius, center.x() + radius, center.y() + radius)
            gradient.setColorAt(0, fill.lighter(108)); gradient.setColorAt(1, fill.darker(108))
            painter.setBrush(gradient)
            painter.setPen(QtGui.QPen(QtGui.QColor(appearance.get("border") or "#f5fbff"), 1.5))
            painter.drawEllipse(center, radius, radius)
            painter.setPen(QtGui.QColor(appearance.get("text") or ("#ffffff" if slot != "y" else "#17394c")))
            font = painter.font(); font.setBold(True); font.setPointSizeF(10); painter.setFont(font)
            painter.drawText(QtCore.QRectF(center.x() - radius, center.y() - radius + 2, radius * 2, 18), QtCore.Qt.AlignCenter, label)
            font.setPointSizeF(6); painter.setFont(font)
            painter.drawText(QtCore.QRectF(center.x() - radius, center.y() + 7, radius * 2, 11), QtCore.Qt.AlignCenter, self._binding(slot))

    def _paint_mouse(self, painter, cx, cy, size):
        rect = QtCore.QRectF(cx - size * .42, cy - size * .28, size * .84, size * .56)
        painter.setBrush(self._appearance_color("fill", "control_fill"))
        painter.setPen(QtGui.QPen(self._appearance_color("border", "control_border"), 1.7, QtCore.Qt.DashLine))
        painter.drawRoundedRect(rect, 10, 10)
        painter.setPen(self._appearance_color("text", "button_text"))
        font = painter.font(); font.setBold(True); font.setPointSizeF(8); painter.setFont(font)
        painter.drawText(rect, QtCore.Qt.AlignCenter, str(self._control.get("label") or "鼠标区域"))

    @staticmethod
    def _paint_caption(painter, cx, top, text):
        painter.setPen(QtGui.QColor("#315864"))
        font = painter.font(); font.setBold(True); font.setPointSizeF(7.5); painter.setFont(font)
        painter.drawText(QtCore.QRectF(cx - 45, top, 90, 16), QtCore.Qt.AlignCenter, text)


class CanvasView(QtWidgets.QWidget):
    control_selected = QtCore.Signal(str)
    item_drag_started = QtCore.Signal()
    item_drag_finished = QtCore.Signal()
    zoom_changed = QtCore.Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("gamepadCanvas")
        self._state = {}
        self._selected_control_id = None
        self._control_items = {}
        self._phone_rect = QtCore.QRectF()
        self._hint_text = ""
        self._zoom = 1.0
        self._background_presets = []
        self._preview_mode = False
        self.setMinimumSize(320, 240)

    def set_state(self, state):
        self._state = state

    def set_background_presets(self, presets):
        self._background_presets = [item for item in presets or [] if isinstance(item, dict)]

    def set_preview_mode(self, enabled):
        self._preview_mode = bool(enabled)

    def active_layout(self):
        layouts = self._state.get("layouts") or []
        active = self._state.get("activeLayoutId")
        return next((item for item in layouts if item.get("id") == active), layouts[0] if layouts else {})

    def set_selected_control(self, control_id):
        self._selected_control_id = control_id or None
        for cid, item in self._control_items.items():
            item.set_selected(not self._preview_mode and cid == self._selected_control_id)
        self.update()

    def set_zoom(self, value):
        value = _clamp(float(value), .55, 1.4)
        if abs(value - self._zoom) < .001:
            return
        self._zoom = value
        self.rebuild()
        self.zoom_changed.emit(int(round(value * 100)))

    def zoom(self):
        return self._zoom

    def fit_to_window(self):
        self.set_zoom(1.0)

    def rebuild(self):
        for item in list(self._control_items.values()):
            item.setParent(None)
            item.deleteLater()
        self._control_items.clear()
        frame_w, frame_h = self._compute_frame_size()
        self._phone_rect = QtCore.QRectF((self.width() - frame_w) / 2, (self.height() - frame_h) / 2, frame_w, frame_h)
        if frame_w <= 0 or frame_h <= 0:
            return
        for control in self.active_layout().get("controls", []):
            self._add_control_item(control)
        self.update()

    def add_control_widget(self, control):
        if self._phone_rect.width() <= 0:
            frame_w, frame_h = self._compute_frame_size()
            self._phone_rect = QtCore.QRectF((self.width() - frame_w) / 2, (self.height() - frame_h) / 2, frame_w, frame_h)
        self._add_control_item(control)
        self.update()

    def _add_control_item(self, control):
        size = self._compute_item_size(control)
        item = ControlItem(control, self)
        item.set_scene_scale(self._frame_scale())
        item.set_visual_theme(self._theme())
        item.set_visual_opacity(float(control.get("opacity", 100)) / 100 * (1 if control.get("visible") is not False else .18))
        item.setGeometry(self._item_rect(control.get("x", 50), control.get("y", 50), size))
        item.clicked.connect(self.control_selected.emit)
        item.drag_started.connect(self.item_drag_started.emit)
        item.drag_finished.connect(self.item_drag_finished.emit)
        item.show()
        item.raise_()
        self._control_items[control["id"]] = item
        item.set_selected(not self._preview_mode and control["id"] == self._selected_control_id)

    def _theme(self):
        return _theme_for_background(self.active_layout().get("background"), self._background_presets)

    def set_background(self, background):
        if not self.active_layout():
            return
        if isinstance(background, str):
            background = {"id": background}
        self.active_layout()["background"] = copy.deepcopy(background)
        self.rebuild()

    def update_control_position(self, control):
        item = self._control_items.get(control.get("id"))
        if item:
            size = self._compute_item_size(control)
            item.setGeometry(self._item_rect(control.get("x", 50), control.get("y", 50), size))

    def update_control_visual(self, control):
        item = self._control_items.get(control.get("id"))
        if item:
            size = self._compute_item_size(control)
            item.setGeometry(self._item_rect(control.get("x", 50), control.get("y", 50), size))
            item.set_visual_theme(self._theme())
            opacity = float(control.get("opacity", 100)) / 100
            item.set_visual_opacity(opacity * (1 if control.get("visible") is not False else .18))
            item.update()

    def position_from_drag(self, start, delta, size_px):
        rect = self._phone_rect
        if rect.width() <= 0 or rect.height() <= 0:
            return start.x(), start.y()
        half_x = min(50, size_px / rect.width() * 50)
        half_y = min(50, size_px / rect.height() * 50)
        return (
            _clamp(start.x() + delta.x() / rect.width() * 100, half_x, 100 - half_x),
            _clamp(start.y() + delta.y() / rect.height() * 100, half_y, 100 - half_y),
        )

    def _canvas_ratio(self):
        canvas = self.active_layout().get("canvas") if isinstance(self.active_layout().get("canvas"), dict) else {}
        width = max(1, float(canvas.get("width", 2400)))
        height = max(1, float(canvas.get("height", 1080)))
        return width / height

    def _compute_frame_size(self):
        ratio = self._canvas_ratio()
        max_w, max_h = max(1, self.width() * .92), max(1, self.height() * .86)
        if max_w / ratio <= max_h:
            fit_w, fit_h = max_w, max_w / ratio
        else:
            fit_h, fit_w = max_h, max_h * ratio
        return fit_w * self._zoom, fit_h * self._zoom

    def _frame_scale(self):
        return max(.01, self._phone_rect.width() / REFERENCE_PHONE_WIDTH)

    def _compute_item_size(self, control):
        ctype = control.get("type", "key")
        base = {
            "leftStick": 184, "rightStick": 158, "abxy": 174, "dpad": 158,
            "mouse": 170, "shoulder": 82, "macro": 88, "key": 78,
        }.get(ctype, 78)
        return base * float(control.get("size", 100)) / 100 * self._frame_scale()

    def _item_rect(self, x, y, size):
        center = QtCore.QPointF(self._phone_rect.x() + self._phone_rect.width() * float(x) / 100, self._phone_rect.y() + self._phone_rect.height() * float(y) / 100)
        side = max(1, int(round(size)))
        return QtCore.QRect(int(center.x() - size / 2), int(center.y() - size / 2), side, side)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.rebuild()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.control_selected.emit("")
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.fillRect(self.rect(), QtGui.QColor("#dce6e9"))
        painter.setPen(QtGui.QPen(QtGui.QColor(91, 119, 128, 22), 1))
        for x in range(0, self.width(), 28):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), 28):
            painter.drawLine(0, y, self.width(), y)
        frame_w, frame_h = self._compute_frame_size()
        self._phone_rect = QtCore.QRectF((self.width() - frame_w) / 2, (self.height() - frame_h) / 2, frame_w, frame_h)
        scale = self._frame_scale()
        shadow = self._phone_rect.adjusted(-2 * scale, 10 * scale, 2 * scale, 18 * scale)
        painter.setBrush(QtGui.QColor(38, 61, 69, 48)); painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(shadow, 25 * scale, 25 * scale)
        painter.setBrush(QtGui.QColor("#263b43"))
        painter.drawRoundedRect(self._phone_rect.adjusted(-5 * scale, -5 * scale, 5 * scale, 5 * scale), 26 * scale, 26 * scale)
        self._paint_scene(painter, self._phone_rect)

    def _paint_scene(self, painter, rect):
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        theme = self._theme(); kind = theme.get("kind", "mobile-light")
        gradient = QtGui.QLinearGradient(x, y, x, y + h)
        gradient.setColorAt(0, QtGui.QColor(theme["stage_top"])); gradient.setColorAt(1, QtGui.QColor(theme["stage_bottom"]))
        painter.setBrush(gradient); painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(rect, 20 * self._frame_scale(), 20 * self._frame_scale())
        if kind == "terrain":
            painter.fillRect(QtCore.QRectF(x, y + h * .48, w, h * .52), QtGui.QColor(theme["stage_bottom"]))
            painter.save(); painter.translate(x + w * .44, y); painter.shear(-.28, 0)
            painter.fillRect(0, 0, w * .15, h, QtGui.QColor("#c8bb7b")); painter.restore()
            for mx, mw, color in [(x + w * .03, w * .34, "#2b6071"), (x + w * .35, w * .36, "#245568"), (x + w * .65, w * .34, "#316878")]:
                path = QtGui.QPainterPath(); path.moveTo(mx, y + h * .33); path.lineTo(mx + mw / 2, y + h * .04); path.lineTo(mx + mw, y + h * .33); path.closeSubpath()
                painter.fillPath(path, QtGui.QColor(color))
        color = QtGui.QColor(theme["grid"])
        color.setAlpha(28 if kind == "mobile-light" else 42 if kind in {"arcade", "paper"} else 18)
        painter.setPen(QtGui.QPen(color, 1))
        step_x, step_y = max(18, int(w / 12)), max(18, int(h / 6))
        for gx in range(0, int(w) + 1, step_x):
            painter.drawLine(x + gx, y, x + gx, y + h)
        for gy in range(0, int(h) + 1, step_y):
            painter.drawLine(x, y + gy, x + w, y + gy)
        camera = QtCore.QRectF(rect.center().x() - 42 * self._frame_scale(), y + 9 * self._frame_scale(), 84 * self._frame_scale(), 7 * self._frame_scale())
        painter.setBrush(QtGui.QColor(38, 61, 69, 205)); painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(camera, 4 * self._frame_scale(), 4 * self._frame_scale())


class ResourceLibraryPanel(QtWidgets.QWidget):
    layout_chosen = QtCore.Signal(str)
    new_layout_requested = QtCore.Signal(str)
    layout_action_requested = QtCore.Signal(str, str)
    background_changed = QtCore.Signal(object)
    save_background_requested = QtCore.Signal()
    delete_background_requested = QtCore.Signal(str)
    add_control = QtCore.Signal(object)
    apply_preset_requested = QtCore.Signal(dict)
    preset_action_requested = QtCore.Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("resourceLibrary")
        self._state = {}; self._presets = []; self._background_presets = []; self._shortcut_actions = _shortcut_actions()
        self.setMinimumWidth(210)
        self.setStyleSheet("""
            QWidget#resourceLibrary { background: #f7fafb; border-right: 1px solid #c9d5da; }
            QLabel { color: #1d2b31; }
            QLabel.sectionTitle { font-size: 11px; font-weight: 800; }
            QLabel.sectionMeta { color: #7d8d93; font-size: 9px; }
            QPushButton.tile { text-align: left; padding: 7px 8px; border: 1px solid #d0dade; border-radius: 5px; background: #ffffff; color: #25343a; font-size: 10px; }
            QPushButton.tile:hover { border-color: #79b8c0; background: #f2fbfb; }
            QPushButton.tile:checked { border: 1px solid #45beba; background: #e8f6f5; color: #176c70; }
            QPushButton.component { text-align: left; padding: 7px; min-height: 38px; border: 1px solid #d0dade; border-radius: 5px; background: #ffffff; color: #24333a; font-size: 9px; }
            QPushButton.component:hover { border-color: #45beba; background: #edf9f8; }
            QToolButton.menu { border: none; color: #718389; background: transparent; font-size: 14px; }
            QToolButton.add { border: none; color: #087d79; background: transparent; font-size: 10px; font-weight: 700; }
            QScrollArea { border: none; background: transparent; }
            QWidget#resourceInner { background: #f7fafb; }
            QComboBox { border: 1px solid #cbd7db; border-radius: 4px; background: #ffffff; padding: 5px; color: #394b52; font-size: 9px; }
        """)
        root = QtWidgets.QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)
        head = QtWidgets.QFrame(); head.setFixedHeight(48); head.setStyleSheet("border-bottom:1px solid #d4dfe3;")
        head_row = QtWidgets.QHBoxLayout(head); head_row.setContentsMargins(12, 0, 10, 0)
        title = QtWidgets.QLabel("资源库"); title.setStyleSheet("font-size:13px;font-weight:800;")
        add = QtWidgets.QToolButton(); add.setText("＋ 新建"); add.setProperty("class", "add"); add.clicked.connect(self._new_layout_menu)
        head_row.addWidget(title); head_row.addStretch(1); head_row.addWidget(add); root.addWidget(head)
        self._scroll = QtWidgets.QScrollArea(); self._scroll.setWidgetResizable(True); self._scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self._inner = QtWidgets.QWidget(); self._inner.setObjectName("resourceInner")
        self._content = QtWidgets.QVBoxLayout(self._inner); self._content.setContentsMargins(12, 10, 12, 14); self._content.setSpacing(0)
        self._scroll.setWidget(self._inner); root.addWidget(self._scroll, 1)

    def _new_layout_menu(self):
        menu = QtWidgets.QMenu(self)
        menu.addAction("空白横屏布局", lambda: self.new_layout_requested.emit("blank"))
        menu.addAction("双摇杆射击布局", lambda: self.new_layout_requested.emit("shooter"))
        menu.exec(QtGui.QCursor.pos())

    def set_data(self, state, presets, backgrounds):
        self._state = state or {}
        self._presets = [item for item in presets or [] if isinstance(item, dict)]
        self._background_presets = [item for item in backgrounds or [] if isinstance(item, dict)]
        self.refresh()

    def refresh(self):
        _clear_layout(self._content)
        self._build_layouts()
        self._separator()
        self._build_backgrounds()
        self._separator()
        self._build_components()
        if self._presets:
            self._separator(); self._build_presets()
        self._content.addStretch(1)

    def _heading(self, title, meta="", action_text="", action=None):
        row = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel(title); label.setProperty("class", "sectionTitle"); row.addWidget(label)
        row.addStretch(1)
        if action_text and action:
            button = QtWidgets.QToolButton(); button.setText(action_text); button.setProperty("class", "add"); button.clicked.connect(action); row.addWidget(button)
        elif meta:
            label_meta = QtWidgets.QLabel(meta); label_meta.setProperty("class", "sectionMeta"); row.addWidget(label_meta)
        self._content.addLayout(row)
        self._content.addSpacing(7)

    def _separator(self):
        line = QtWidgets.QFrame(); line.setFrameShape(QtWidgets.QFrame.HLine); line.setStyleSheet("color:#d4dfe3;")
        self._content.addSpacing(12); self._content.addWidget(line); self._content.addSpacing(12)

    def _build_layouts(self):
        layouts = self._state.get("layouts") or []
        active = self._state.get("activeLayoutId")
        self._heading("我的布局", str(len(layouts)) + " 个")
        for layout in layouts:
            row = QtWidgets.QHBoxLayout(); row.setSpacing(4)
            canvas = layout.get("canvas") or {}; count = len(layout.get("controls") or [])
            button = QtWidgets.QPushButton(f"{layout.get('name','未命名布局')}\n{count} 个组件 · {canvas.get('width',2400)}×{canvas.get('height',1080)}")
            button.setCheckable(True); button.setChecked(layout.get("id") == active); button.setProperty("class", "tile")
            button.clicked.connect(lambda checked=False, value=layout.get("id"): self.layout_chosen.emit(value)); row.addWidget(button, 1)
            more = QtWidgets.QToolButton(); more.setText("⋯"); more.setProperty("class", "menu"); more.setFixedWidth(22)
            more.clicked.connect(lambda checked=False, value=layout.get("id"): self._layout_menu(value)); row.addWidget(more)
            self._content.addLayout(row); self._content.addSpacing(5)

    def _layout_menu(self, layout_id):
        menu = QtWidgets.QMenu(self)
        menu.addAction("重命名", lambda: self.layout_action_requested.emit("rename", layout_id))
        menu.addAction("复制布局", lambda: self.layout_action_requested.emit("duplicate", layout_id))
        menu.addSeparator()
        menu.addAction("删除布局", lambda: self.layout_action_requested.emit("delete", layout_id))
        menu.exec(QtGui.QCursor.pos())

    def _build_backgrounds(self):
        self._heading("背景方案", "", "保存当前", self.save_background_requested.emit)
        current_id = ((next((item for item in self._state.get("layouts") or [] if item.get("id") == self._state.get("activeLayoutId")), {}) or {}).get("background") or {}).get("id")
        grid = QtWidgets.QGridLayout(); grid.setSpacing(6)
        backgrounds = [{"id": key, "name": value["title"], "baseId": key} for key, value in BACKGROUND_PRESETS.items()]
        backgrounds.extend(self._background_presets)
        for index, background in enumerate(backgrounds):
            theme = _theme_for_background(background, self._background_presets)
            button = QtWidgets.QPushButton(background.get("name") or theme.get("title") or "背景")
            button.setCheckable(True); button.setChecked(background.get("id") == current_id); button.setProperty("class", "tile")
            button.setMinimumHeight(42)
            button.setStyleSheet(f"QPushButton{{border-top:8px solid {theme['stage_top']};}}")
            button.clicked.connect(lambda checked=False, value=copy.deepcopy(background): self.background_changed.emit(value))
            if background.get("id") not in BACKGROUND_PRESETS:
                button.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
                button.customContextMenuRequested.connect(lambda pos, value=background.get("id"): self._background_menu(value))
            grid.addWidget(button, index // 2, index % 2)
        self._content.addLayout(grid)

    def _background_menu(self, background_id):
        menu = QtWidgets.QMenu(self)
        menu.addAction("删除背景预设", lambda: self.delete_background_requested.emit(background_id))
        menu.exec(QtGui.QCursor.pos())

    def _build_components(self):
        self._heading("组件库", "拖入画布")
        combo = QtWidgets.QComboBox(); combo.addItems(["Switch", "通用", "街机", "快捷键"]); self._content.addWidget(combo); self._content.addSpacing(7)
        container = QtWidgets.QWidget(); grid = QtWidgets.QGridLayout(container); grid.setContentsMargins(0, 0, 0, 0); grid.setSpacing(6)
        self._component_container = container; self._component_grid = grid
        self._content.addWidget(container)
        combo.currentTextChanged.connect(self._populate_component_pack)
        self._populate_component_pack("Switch")

    def _component_specs(self, pack):
        if pack == "Switch":
            return [
                {"type": "leftStick", "title": "移动摇杆", "sub": "自动绑定 WASD"},
                {"type": "abxy", "title": "ABXY", "sub": "四色动作键"},
                {"type": "shoulder", "title": "肩键", "sub": "Switch 青色"},
                {"type": "rightStick", "title": "视角摇杆", "sub": "鼠标视角"},
            ]
        if pack == "街机":
            return [
                {"type": "leftStick", "title": "街机摇杆", "sub": "高对比霓虹", "appearance": {"fill": "#522c69", "border": "#e277ff", "text": "#ffffff"}},
                {"type": "key", "title": "红色动作键", "sub": "圆形大按钮", "appearance": {"shape": "round", "fill": "#e84f61", "border": "#ffd3d8", "text": "#ffffff"}, "size": 125},
                {"type": "key", "title": "黄色动作键", "sub": "圆形大按钮", "appearance": {"shape": "round", "fill": "#f2bc35", "border": "#fff0b3", "text": "#263238"}, "size": 125},
                {"type": "dpad", "title": "街机方向键", "sub": "方向控制", "appearance": {"fill": "#342042", "border": "#db73ff", "text": "#ffffff"}},
            ]
        if pack == "快捷键":
            specs = [{"type": "macro", "title": "自定义快捷键", "sub": "录入组合键"}]
            for action in self._shortcut_actions[:11]:
                specs.append({"type": "macro", "title": action["label"], "sub": action["group"], "label": action["label"], "bindings": {"press": action["binding"]}})
            return specs
        return [{"type": key, "title": value["title"], "sub": value["mode"]} for key, value in TYPE_INFO.items()]

    def _populate_component_pack(self, pack):
        _clear_layout(self._component_grid)
        for index, spec in enumerate(self._component_specs(pack)):
            button = QtWidgets.QPushButton(f"{spec['title']}\n{spec.get('sub','')}")
            button.setProperty("class", "component")
            button.clicked.connect(lambda checked=False, value=copy.deepcopy(spec): self.add_control.emit(value))
            self._component_grid.addWidget(button, index // 2, index % 2)

    def _build_presets(self):
        self._heading("组件预设", str(len(self._presets)) + " 个")
        for preset in self._presets[:20]:
            row = QtWidgets.QHBoxLayout(); row.setSpacing(4)
            button = QtWidgets.QPushButton("＋ " + preset.get("name", "未命名预设")); button.setProperty("class", "tile")
            button.clicked.connect(lambda checked=False, value=preset: self.apply_preset_requested.emit(value)); row.addWidget(button, 1)
            more = QtWidgets.QToolButton(); more.setText("⋯"); more.setProperty("class", "menu"); more.setFixedWidth(22)
            more.clicked.connect(lambda checked=False, value=preset: self._preset_menu(value)); row.addWidget(more)
            self._content.addLayout(row); self._content.addSpacing(4)

    def _preset_menu(self, preset):
        menu = QtWidgets.QMenu(self)
        menu.addAction("重命名", lambda: self.preset_action_requested.emit("rename", preset))
        menu.addAction("删除", lambda: self.preset_action_requested.emit("delete", preset))
        menu.exec(QtGui.QCursor.pos())


# Backward-compatible name used by older tests and handoff notes.
LayoutListPanel = ResourceLibraryPanel


class BindingEditorDialog(QtWidgets.QDialog):
    def __init__(self, binding=None, title="设置按键", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title); self.setModal(True); self.resize(520, 470); self._capturing = False; self._result = None
        self.setStyleSheet("""
            QDialog { background:#f7fafb; color:#1d2b31; font-family:"Microsoft YaHei UI"; }
            QLabel { color:#3f5158; }
            QLineEdit, QComboBox { background:#ffffff; color:#26383f; border:1px solid #c7d4d9; border-radius:5px; padding:7px; min-height:28px; }
            QPushButton, QToolButton { background:#ffffff; color:#33474f; border:1px solid #c5d3d8; border-radius:5px; padding:7px; }
            QPushButton:hover, QToolButton:hover { border-color:#55a7aa; background:#edf8f7; }
            QToolButton:checked { background:#2f78e5; color:#ffffff; border-color:#2f78e5; }
        """)
        root = QtWidgets.QVBoxLayout(self); root.setContentsMargins(20, 18, 20, 18); root.setSpacing(10)
        heading = QtWidgets.QLabel(title); heading.setStyleSheet("font-size:16px;font-weight:800;color:#1d2b31;"); root.addWidget(heading)
        note = QtWidgets.QLabel("组件直接绑定普通键或组合键，不会创建独立字母对象。"); note.setStyleSheet("color:#74858c;font-size:10px;"); root.addWidget(note)
        actions = _shortcut_actions()
        if actions:
            root.addWidget(QtWidgets.QLabel("复用现有快捷键"))
            self._preset_combo = QtWidgets.QComboBox(); self._preset_combo.addItem("选择 Windows、VS Code、Office 等现有动作", None)
            for action in actions:
                self._preset_combo.addItem(f"{action['group']} · {action['label']} · {_binding_display(action['binding'])}", action["binding"])
            self._preset_combo.currentIndexChanged.connect(self._preset_selected); root.addWidget(self._preset_combo)
        else:
            self._preset_combo = None
        root.addWidget(QtWidgets.QLabel("修饰键"))
        mods = QtWidgets.QHBoxLayout(); self._mod_buttons = {}
        current_mods = {str(value).lower() for value in (binding or {}).get("modifiers") or []}
        for value, label in MODIFIER_LABELS.items():
            button = QtWidgets.QToolButton(); button.setText(label); button.setCheckable(True); button.setChecked(value in current_mods); button.setMinimumWidth(86)
            mods.addWidget(button); self._mod_buttons[value] = button
        mods.addStretch(1); root.addLayout(mods)
        root.addWidget(QtWidgets.QLabel("主按键"))
        key_row = QtWidgets.QHBoxLayout(); self._key_edit = QtWidgets.QLineEdit(_key_display((binding or {}).get("key", "")) if binding else ""); self._key_edit.setPlaceholderText("例如 S、Space、F12"); key_row.addWidget(self._key_edit, 1)
        self._capture = QtWidgets.QPushButton("录入实体键"); self._capture.clicked.connect(self._start_capture); key_row.addWidget(self._capture); root.addLayout(key_row)
        root.addWidget(QtWidgets.QLabel("常用键"))
        common = QtWidgets.QGridLayout(); common.setSpacing(5)
        for index, value in enumerate(COMMON_KEYS):
            button = QtWidgets.QPushButton(value); button.clicked.connect(lambda checked=False, key=value: self._set_key(key)); common.addWidget(button, index // 7, index % 7)
        root.addLayout(common); root.addStretch(1)
        action_row = QtWidgets.QHBoxLayout(); action_row.addStretch(1)
        cancel = QtWidgets.QPushButton("取消"); cancel.clicked.connect(self.reject); action_row.addWidget(cancel)
        save = QtWidgets.QPushButton("应用绑定"); save.setStyleSheet("background:#43cfc8;color:#082b2b;border-color:#43cfc8;font-weight:800;"); save.clicked.connect(self._accept_binding); action_row.addWidget(save); root.addLayout(action_row)

    def _preset_selected(self):
        binding = self._preset_combo.currentData() if self._preset_combo else None
        if not isinstance(binding, dict):
            return
        current = {str(value).lower() for value in binding.get("modifiers") or []}
        for name, button in self._mod_buttons.items():
            button.setChecked(name in current)
        self._key_edit.setText(_key_display(binding.get("key")))

    def _set_key(self, value):
        self._key_edit.setText(value)

    def _start_capture(self):
        self._capturing = True; self._capture.setText("请按键…"); self._capture.setStyleSheet("border-color:#2f9f9a;color:#087c78;"); self.grabKeyboard()

    def keyPressEvent(self, event):
        if not self._capturing:
            if event.key() == QtCore.Qt.Key_Escape:
                self.reject(); return
            super().keyPressEvent(event); return
        key = _qt_key_name(event.key())
        if not key and event.text():
            key = event.text().lower()
        if not key:
            return
        modifiers = event.modifiers()
        for name, flag in [("ctrl", QtCore.Qt.ControlModifier), ("shift", QtCore.Qt.ShiftModifier), ("alt", QtCore.Qt.AltModifier), ("win", QtCore.Qt.MetaModifier)]:
            self._mod_buttons[name].setChecked(bool(modifiers & flag) and key != name)
        self._key_edit.setText(_key_display(key)); self._capturing = False; self.releaseKeyboard(); self._capture.setText("录入实体键"); self._capture.setStyleSheet(""); event.accept()

    def _accept_binding(self):
        raw = {"key": self._key_edit.text(), "modifiers": [name for name, button in self._mod_buttons.items() if button.isChecked()]}
        binding = gamepad_layouts_loader._normalize_binding(raw)
        if not binding:
            QtWidgets.QMessageBox.warning(self, "无法保存", "请设置一个有效的主按键。"); return
        self._result = binding; self.accept()

    @classmethod
    def get_binding(cls, parent, binding, title):
        dialog = cls(binding, title, parent)
        return dialog._result if dialog.exec() == QtWidgets.QDialog.Accepted else None


class InspectorPanel(QtWidgets.QWidget):
    request_export = QtCore.Signal()
    control_change_started = QtCore.Signal()
    property_changed = QtCore.Signal()
    duplicate_control_clicked = QtCore.Signal()
    delete_control_clicked = QtCore.Signal()
    save_preset_requested = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("inspectorPanel"); self._state = {}; self._selected_control_id = None; self._presets = []
        self.setMinimumWidth(280)
        self.setStyleSheet("""
            QWidget#inspectorPanel { background:#f7fafb; border-left:1px solid #c8d4d9; color:#1d2b31; }
            QScrollArea { background:transparent; border:none; }
            QWidget#inspectorInner { background:#f7fafb; }
            QLabel { color:#394b52; font-size:10px; }
            QLabel.sectionTitle { color:#1d2b31; font-size:11px; font-weight:800; }
            QLabel.muted { color:#7d8d93; font-size:8px; }
            QLineEdit, QComboBox { border:1px solid #c7d4d9; border-radius:5px; padding:6px; color:#26383f; background:#ffffff; min-height:28px; }
            QPushButton { border:1px solid #c7d4d9; border-radius:5px; padding:6px; color:#33474f; background:#ffffff; }
            QPushButton:hover { border-color:#55a7aa; background:#edf8f7; }
            QPushButton.bind { text-align:left; min-height:34px; border-color:#c5d4da; font-size:9px; }
            QPushButton.bind:hover { border-color:#2f78e5; }
            QPushButton.shape { min-height:30px; font-size:9px; }
            QPushButton.shape:checked { border:2px solid #2baea9; background:#e9f8f7; color:#087c78; }
            QPushButton.primary { background:#e7f7f5; color:#087c78; border-color:#309f9b; font-weight:800; }
            QToolButton { border:1px solid #c7d4d9; border-radius:4px; background:#ffffff; color:#63757c; }
            QCheckBox::indicator { width:30px; height:16px; }
            QSlider::groove:horizontal { height:3px; background:#c5d2d6; border-radius:2px; }
            QSlider::sub-page:horizontal { background:#2f80e8; border-radius:2px; }
            QSlider::handle:horizontal { background:#2f80e8; width:12px; margin:-5px 0; border-radius:6px; }
        """)
        root = QtWidgets.QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)
        head = QtWidgets.QFrame(); head.setFixedHeight(48); head.setStyleSheet("border-bottom:1px solid #d4dfe3;")
        row = QtWidgets.QHBoxLayout(head); row.setContentsMargins(14, 0, 10, 0)
        title = QtWidgets.QLabel("组件属性"); title.setStyleSheet("font-size:13px;font-weight:800;")
        export = QtWidgets.QToolButton(); export.setText("···"); export.setFixedSize(28, 26); export.setToolTip("导出 JSON"); export.clicked.connect(self.request_export.emit)
        row.addWidget(title); row.addStretch(1); row.addWidget(export); root.addWidget(head)
        self._scroll = QtWidgets.QScrollArea(); self._scroll.setWidgetResizable(True); self._scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self._inner = QtWidgets.QWidget(); self._inner.setObjectName("inspectorInner")
        self._layout = QtWidgets.QVBoxLayout(self._inner); self._layout.setContentsMargins(0, 0, 0, 12); self._layout.setSpacing(0)
        self._scroll.setWidget(self._inner); root.addWidget(self._scroll, 1)

    def set_state(self, state):
        self._state = state

    def set_selected_control(self, value):
        self._selected_control_id = value or None
        self.refresh()

    def set_presets(self, presets):
        self._presets = presets or []

    def set_history(self, history_len, future_len):
        pass

    def active_layout(self):
        layouts = self._state.get("layouts") or []; active = self._state.get("activeLayoutId")
        return next((item for item in layouts if item.get("id") == active), layouts[0] if layouts else {})

    def selected_control(self):
        return next((item for item in self.active_layout().get("controls", []) if item.get("id") == self._selected_control_id), None)

    def refresh(self):
        _clear_layout(self._layout)
        control = self.selected_control()
        if not control:
            empty = QtWidgets.QLabel("在画布中选择一个组件，\n或从左侧组件库添加。"); empty.setAlignment(QtCore.Qt.AlignCenter); empty.setStyleSheet("color:#7c8e95;font-size:11px;padding:42px 20px;")
            self._layout.addWidget(empty); self._layout.addStretch(1); return
        self._build_header(control); self._build_basic(control); self._build_bindings(control); self._build_visual(control); self._build_actions(); self._layout.addStretch(1)

    def _block(self):
        frame = QtWidgets.QFrame(); frame.setStyleSheet("border-bottom:1px solid #d4dfe3;")
        layout = QtWidgets.QVBoxLayout(frame); layout.setContentsMargins(14, 12, 14, 12); layout.setSpacing(7)
        self._layout.addWidget(frame); return layout

    @staticmethod
    def _heading(layout, title, meta=""):
        row = QtWidgets.QHBoxLayout(); label = QtWidgets.QLabel(title); label.setProperty("class", "sectionTitle"); row.addWidget(label); row.addStretch(1)
        if meta:
            value = QtWidgets.QLabel(meta); value.setProperty("class", "muted"); row.addWidget(value)
        layout.addLayout(row)

    def _build_header(self, control):
        layout = self._block(); row = QtWidgets.QHBoxLayout()
        icon = QtWidgets.QLabel(TYPE_INFO.get(control.get("type"), TYPE_INFO["key"])["icon"]); icon.setAlignment(QtCore.Qt.AlignCenter); icon.setFixedSize(42, 42); icon.setStyleSheet("border-radius:21px;background:#3f91f2;color:white;font-weight:800;")
        copy_box = QtWidgets.QVBoxLayout(); name = QtWidgets.QLabel(control.get("label", "组件")); name.setStyleSheet("font-size:11px;font-weight:800;")
        sub = QtWidgets.QLabel("Switch · " + TYPE_INFO.get(control.get("type"), TYPE_INFO["key"])["mode"]); sub.setProperty("class", "muted")
        copy_box.addWidget(name); copy_box.addWidget(sub); row.addWidget(icon); row.addLayout(copy_box, 1); layout.addLayout(row)

    def _build_basic(self, control):
        layout = self._block(); self._heading(layout, "基础", f"位置 {control.get('x',50):.0f}%, {control.get('y',50):.0f}%")
        label = QtWidgets.QLabel("组件名称"); label.setProperty("class", "muted"); layout.addWidget(label)
        name = QtWidgets.QLineEdit(control.get("label", "")); name.editingFinished.connect(lambda: self._change_value("label", name.text().strip() or "按键")); layout.addWidget(name)

    def _build_bindings(self, control):
        slots = TYPE_INFO.get(control.get("type"), TYPE_INFO["key"])["slots"]
        if not slots:
            if control.get("type") in {"rightStick", "mouse"}:
                layout = self._block(); self._heading(layout, "操作设置")
                row = QtWidgets.QHBoxLayout(); row.addWidget(QtWidgets.QLabel("鼠标灵敏度")); slider = QtWidgets.QSlider(QtCore.Qt.Horizontal); slider.setRange(1, 100); slider.setValue(int(control.get("sensitivity", 55))); slider.sliderPressed.connect(self.control_change_started.emit); slider.valueChanged.connect(lambda value: self._change_value("sensitivity", value, snapshot=False)); row.addWidget(slider, 1); layout.addLayout(row)
            return
        layout = self._block(); self._heading(layout, "直接绑定", "点击修改")
        grid = QtWidgets.QGridLayout(); grid.setSpacing(6)
        for index, slot in enumerate(slots):
            button = QtWidgets.QPushButton(f"{SLOT_LABELS.get(slot,slot)}     {_binding_display((control.get('bindings') or {}).get(slot))}"); button.setProperty("class", "bind")
            button.clicked.connect(lambda checked=False, value=slot: self._edit_binding(value)); button.setContextMenuPolicy(QtCore.Qt.CustomContextMenu); button.customContextMenuRequested.connect(lambda pos, value=slot: self._clear_binding(value)); grid.addWidget(button, index // 2, index % 2)
        layout.addLayout(grid)

    def _build_visual(self, control):
        layout = self._block(); self._heading(layout, "外观", "响应式")
        if control.get("type") in {"key", "shoulder", "macro"}:
            shape_label = QtWidgets.QLabel("按钮形状"); shape_label.setProperty("class", "muted"); layout.addWidget(shape_label)
            shape_row = QtWidgets.QHBoxLayout(); current = (control.get("appearance") or {}).get("shape", "round")
            group = QtWidgets.QButtonGroup(self); group.setExclusive(True)
            for value, title in [("round", "圆形"), ("pill", "胶囊"), ("square", "方形"), ("diamond", "菱形")]:
                button = QtWidgets.QPushButton(title); button.setCheckable(True); button.setChecked(current == value); button.setProperty("class", "shape"); button.clicked.connect(lambda checked=False, key=value: self._change_appearance("shape", key)); group.addButton(button); shape_row.addWidget(button)
            layout.addLayout(shape_row)
        color_label = QtWidgets.QLabel("颜色"); color_label.setProperty("class", "muted"); layout.addWidget(color_label)
        colors = QtWidgets.QHBoxLayout()
        appearance = control.get("appearance") or {}
        defaults = {"fill": "#3f91f2", "border": "#b8def6", "text": "#ffffff"}
        for field, title in [("fill", "填充"), ("border", "描边"), ("text", "文字")]:
            color = appearance.get(field) or defaults[field]
            button = QtWidgets.QPushButton(f"{title}\n{color.upper()}"); button.setStyleSheet(f"QPushButton{{border-left:12px solid {color};font-size:8px;}}"); button.clicked.connect(lambda checked=False, key=field: self._choose_color(key)); colors.addWidget(button)
        layout.addLayout(colors)
        self._build_size_control(layout, control)
        row = QtWidgets.QHBoxLayout(); row.addWidget(QtWidgets.QLabel("不透明度")); slider = QtWidgets.QSlider(QtCore.Qt.Horizontal); slider.setRange(10, 100); slider.setValue(int(control.get("opacity", 100))); output = QtWidgets.QLabel(str(int(control.get("opacity", 100))) + "%"); output.setFixedWidth(34); output.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        slider.sliderPressed.connect(self.control_change_started.emit); slider.valueChanged.connect(lambda number, value=output: (value.setText(str(number) + "%"), self._change_value("opacity", number, snapshot=False))); row.addWidget(slider, 1); row.addWidget(output); layout.addLayout(row)
        for field, title in [("visible", "在手机上显示"), ("locked", "锁定画布位置")]:
            row = QtWidgets.QHBoxLayout(); row.addWidget(QtWidgets.QLabel(title)); row.addStretch(1); check = QtWidgets.QCheckBox(); check.setChecked(bool(control.get(field, field == "visible"))); check.toggled.connect(lambda value, key=field: self._change_value(key, value)); row.addWidget(check); layout.addLayout(row)

    def _build_size_control(self, layout, control):
        current = max(MIN_CONTROL_SIZE, int(round(float(control.get("size", 100)))))
        slider_max = max(INITIAL_SIZE_SLIDER_MAX, ((current // 200) + 2) * 200)
        row = QtWidgets.QHBoxLayout()
        row.addWidget(QtWidgets.QLabel("组件大小"))
        slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        slider.setObjectName("controlSizeSlider")
        slider.setRange(MIN_CONTROL_SIZE, slider_max)
        slider.setValue(current)
        output = QtWidgets.QLineEdit(str(current) + "%")
        output.setObjectName("controlSizeInput")
        output.setFixedWidth(54)
        output.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        output.setToolTip("可直接输入任意大于等于 50% 的数值")

        def apply_slider_value(number):
            # 拖到右端时自动扩大量程；200% 不再是数据或交互上限。
            if number >= slider.maximum() and slider.maximum() < 2_000_000_000:
                slider.setMaximum(min(2_000_000_000, slider.maximum() * 2))
            output.setText(str(number) + "%")
            self._change_value("size", number, snapshot=False)

        def apply_text_value():
            raw = output.text().strip().rstrip("%").strip()
            try:
                number = max(MIN_CONTROL_SIZE, int(round(float(raw))))
            except (TypeError, ValueError, OverflowError):
                output.setText(str(int(round(float(control.get("size", 100))))) + "%")
                return
            if number > slider.maximum():
                expanded = max(number * 2, slider.maximum() * 2)
                slider.setMaximum(min(2_000_000_000, expanded))
            slider.blockSignals(True)
            slider.setValue(min(number, slider.maximum()))
            slider.blockSignals(False)
            output.setText(str(number) + "%")
            self._change_value("size", number)

        slider.sliderPressed.connect(self.control_change_started.emit)
        slider.valueChanged.connect(apply_slider_value)
        output.editingFinished.connect(apply_text_value)
        row.addWidget(slider, 1)
        row.addWidget(output)
        layout.addLayout(row)

    def _build_actions(self):
        layout = self._block(); save = QtWidgets.QPushButton("◇ 保存为组件预设"); save.setProperty("class", "primary"); save.clicked.connect(self.save_preset_requested.emit); layout.addWidget(save)
        row = QtWidgets.QHBoxLayout(); duplicate = QtWidgets.QPushButton("复制组件"); duplicate.clicked.connect(self.duplicate_control_clicked.emit); row.addWidget(duplicate)
        delete = QtWidgets.QPushButton("删除组件"); delete.setStyleSheet("color:#ba3946;border-color:#e4b4ba;"); delete.clicked.connect(self.delete_control_clicked.emit); row.addWidget(delete); layout.addLayout(row)

    def _change_value(self, field, value, snapshot=True):
        control = self.selected_control()
        if not control:
            return
        if snapshot:
            self.control_change_started.emit()
        control[field] = value; self.property_changed.emit()
        if field in {"label", "visible", "locked"}:
            self.refresh()

    def _change_appearance(self, field, value):
        control = self.selected_control()
        if not control:
            return
        self.control_change_started.emit(); control.setdefault("appearance", {})[field] = value; self.property_changed.emit(); self.refresh()

    def _choose_color(self, field):
        control = self.selected_control()
        if not control:
            return
        current = QtGui.QColor((control.get("appearance") or {}).get(field, "#3f91f2")); color = QtWidgets.QColorDialog.getColor(current, self, "选择颜色")
        if color.isValid():
            self._change_appearance(field, color.name())

    def _edit_binding(self, slot):
        control = self.selected_control()
        if not control:
            return
        binding = BindingEditorDialog.get_binding(self, (control.get("bindings") or {}).get(slot), "设置" + SLOT_LABELS.get(slot, "按键"))
        if binding:
            self.control_change_started.emit(); control.setdefault("bindings", {})[slot] = binding; self.property_changed.emit(); self.refresh()

    def _clear_binding(self, slot):
        control = self.selected_control()
        if not control or slot not in (control.get("bindings") or {}):
            return
        self.control_change_started.emit(); control["bindings"].pop(slot, None); self.property_changed.emit(); self.refresh()


class PreviewDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent); self.setWindowTitle("手机横屏预览"); self.resize(960, 520); self.setStyleSheet("background:#dce6e9;color:#1d2b31;font-family:'Microsoft YaHei UI';")
        root = QtWidgets.QVBoxLayout(self); root.setContentsMargins(16, 12, 16, 14)
        title = QtWidgets.QLabel("手机横屏预览"); title.setStyleSheet("font-size:14px;font-weight:800;"); root.addWidget(title)
        self._canvas = CanvasView(); self._canvas.set_preview_mode(True); self._canvas.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True); root.addWidget(self._canvas, 1)
        close = QtWidgets.QPushButton("关闭"); close.clicked.connect(self.close); row = QtWidgets.QHBoxLayout(); row.addStretch(1); row.addWidget(close); root.addLayout(row)

    def set_layout(self, layout_data, backgrounds=None):
        layout = copy.deepcopy(layout_data); layout["controls"] = [item for item in layout.get("controls", []) if item.get("visible") is not False]
        self._canvas.set_background_presets(backgrounds or []); self._canvas.set_state({"activeLayoutId": "preview", "layouts": [dict(layout, id="preview")]}); self._canvas.rebuild()


class CanvasSizeDialog(QtWidgets.QDialog):
    @classmethod
    def get_size(cls, parent, width, height):
        dialog = cls(parent); dialog.setWindowTitle("自定义画布尺寸"); dialog.setModal(True); dialog.setStyleSheet("QDialog{background:#f7fafb;} QLabel{color:#35474e;} QSpinBox{padding:6px;border:1px solid #c7d4d9;border-radius:4px;background:white;}")
        layout = QtWidgets.QFormLayout(dialog); layout.setContentsMargins(18, 16, 18, 16)
        w = QtWidgets.QSpinBox(); w.setRange(640, 7680); w.setValue(int(width)); w.setSuffix(" px")
        h = QtWidgets.QSpinBox(); h.setRange(360, 4320); h.setValue(int(height)); h.setSuffix(" px")
        layout.addRow("宽度", w); layout.addRow("高度", h)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel); buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject); layout.addRow(buttons)
        return (w.value(), h.value(), True) if dialog.exec() == QtWidgets.QDialog.Accepted else (width, height, False)


class EditorPage(QtWidgets.QWidget):
    status_message = QtCore.Signal(str)
    back_requested = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("desktopGamepadEditor"); self.setStyleSheet(EDITOR_STYLE)
        self._state = {}; self._history = []; self._future = []; self._dirty = False
        self._component_presets = []; self._background_presets = []; self._preview_dialog = None
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)
        toolbar = QtWidgets.QFrame(); toolbar.setFixedHeight(56); toolbar.setStyleSheet("background:#17252c;border-bottom:1px solid #0e181d;color:#eaf3f5;")
        row = QtWidgets.QHBoxLayout(toolbar); row.setContentsMargins(12, 0, 14, 0); row.setSpacing(8)
        back = QtWidgets.QToolButton(); back.setText("←"); back.setFixedSize(32, 32); back.setToolTip("返回配对"); back.setStyleSheet("QToolButton{border:1px solid #3c5059;border-radius:5px;color:#d7e5e8;background:#22343c;font-size:17px;}"); back.clicked.connect(self.back_requested.emit); row.addWidget(back)
        mark = QtWidgets.QLabel("PK"); mark.setAlignment(QtCore.Qt.AlignCenter); mark.setFixedSize(30, 30); mark.setStyleSheet("background:#45d7d0;color:#082a2d;border-radius:6px;font-weight:900;"); row.addWidget(mark)
        brand = QtWidgets.QLabel("控制台布局  <span style='color:#8fa5ad;font-size:9px'>PhoneKB Studio</span>"); brand.setStyleSheet("font-size:13px;font-weight:800;color:#eef7f8;"); brand.setMinimumWidth(220); row.addWidget(brand)
        self._layout_title = QtWidgets.QLabel("Switch 标准布局"); self._layout_title.setStyleSheet("color:#eef7f8;font-size:12px;font-weight:800;"); row.addWidget(self._layout_title)
        self._canvas_tag = QtWidgets.QToolButton(); self._canvas_tag.setPopupMode(QtWidgets.QToolButton.InstantPopup); self._canvas_tag.setStyleSheet("QToolButton{border:1px solid #425760;border-radius:4px;color:#afc2c9;background:transparent;padding:5px 8px;font-size:9px;}")
        menu = QtWidgets.QMenu(self._canvas_tag)
        for title, width, height in CANVAS_PRESETS:
            menu.addAction(title, lambda checked=False, w=width, h=height: self._set_canvas_size(w, h))
        menu.addSeparator(); menu.addAction("自定义尺寸…", self._custom_canvas_size); self._canvas_tag.setMenu(menu); row.addWidget(self._canvas_tag)
        tag = QtWidgets.QLabel("单层组件"); tag.setStyleSheet("border:1px solid #425760;border-radius:4px;color:#afc2c9;padding:5px 8px;font-size:9px;"); row.addWidget(tag); row.addStretch(1)
        self._undo_btn = self._top_button("↶", "撤销"); self._undo_btn.clicked.connect(self._undo); row.addWidget(self._undo_btn)
        self._redo_btn = self._top_button("↷", "重做"); self._redo_btn.clicked.connect(self._redo); row.addWidget(self._redo_btn)
        preview = self._top_button("▣  手机预览", "手机预览", wide=True); preview.clicked.connect(self._open_preview); row.addWidget(preview)
        save = self._top_button("✓  保存并同步", "保存布局", wide=True, primary=True); save.clicked.connect(self._save); row.addWidget(save); root.addWidget(toolbar)

        body = QtWidgets.QWidget(); body_row = QtWidgets.QHBoxLayout(body); body_row.setContentsMargins(0, 0, 0, 0); body_row.setSpacing(0)
        rail = QtWidgets.QFrame(); rail.setFixedWidth(50); rail.setStyleSheet("background:#1c2b32;border-right:1px solid #102027;")
        rail_layout = QtWidgets.QVBoxLayout(rail); rail_layout.setContentsMargins(7, 10, 7, 8); rail_layout.setSpacing(7)
        for index, (text, tip) in enumerate([("▦", "布局"), ("＋", "组件"), ("◫", "背景"), ("◇", "预设")]):
            button = QtWidgets.QToolButton(); button.setText(text); button.setToolTip(tip); button.setFixedSize(36, 36)
            button.setStyleSheet("QToolButton{border:none;border-radius:5px;color:%s;background:%s;font-size:14px;font-weight:800;}" % ("#071f22" if index == 0 else "#9db0b7", "#48d6cf" if index == 0 else "transparent")); rail_layout.addWidget(button)
        rail_layout.addStretch(1); settings = QtWidgets.QToolButton(); settings.setText("⚙"); settings.setFixedSize(36, 36); settings.setStyleSheet("border:none;color:#9db0b7;background:transparent;"); rail_layout.addWidget(settings); body_row.addWidget(rail)

        self._splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal); self._splitter.setHandleWidth(1); self._splitter.setChildrenCollapsible(True); self._splitter.setStyleSheet("QSplitter::handle{background:#c5d1d5;}")
        self._list_panel = ResourceLibraryPanel(); self._wire_library(); self._splitter.addWidget(self._list_panel)
        center = self._build_center(); self._splitter.addWidget(center)
        self._inspector = InspectorPanel(); self._wire_inspector(); self._splitter.addWidget(self._inspector)
        self._splitter.setStretchFactor(0, 0); self._splitter.setStretchFactor(1, 1); self._splitter.setStretchFactor(2, 0); self._splitter.setSizes([254, 900, 332])
        body_row.addWidget(self._splitter, 1); root.addWidget(body, 1)

    def _top_button(self, text, tooltip, wide=False, primary=False):
        button = QtWidgets.QPushButton(text); button.setToolTip(tooltip); button.setFixedHeight(30)
        if not wide:
            button.setFixedWidth(34)
        if primary:
            button.setStyleSheet("QPushButton{border:1px solid #44d4cd;border-radius:5px;background:#44d4cd;color:#07272a;padding:0 12px;font-size:10px;font-weight:800;}")
        else:
            button.setStyleSheet("QPushButton{border:1px solid #3c5059;border-radius:5px;background:#22343c;color:#d7e5e8;padding:0 10px;font-size:10px;} QPushButton:hover{border-color:#6f929f;}")
        return button

    def _build_center(self):
        center = QtWidgets.QWidget(); center.setStyleSheet("background:#dce6e9;")
        layout = QtWidgets.QVBoxLayout(center); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(0)
        tools = QtWidgets.QFrame(); tools.setFixedHeight(44); tools.setStyleSheet("background:#edf2f4;border-bottom:1px solid #c4d0d5;")
        row = QtWidgets.QHBoxLayout(tools); row.setContentsMargins(14, 0, 14, 0); row.setSpacing(7)
        edit = QtWidgets.QPushButton("编辑布局"); edit.setStyleSheet("background:#32474f;color:white;border:none;border-radius:4px;padding:6px 12px;font-size:9px;"); row.addWidget(edit)
        run = QtWidgets.QPushButton("运行预览"); run.setStyleSheet("background:#f8fafb;color:#6a7a80;border:1px solid #bdcbd0;border-radius:4px;padding:5px 12px;font-size:9px;"); run.clicked.connect(self._open_preview); row.addWidget(run)
        for text in ("选择", "对齐", "吸附 8 px"):
            label = QtWidgets.QLabel(text); label.setStyleSheet("color:#62747b;font-size:9px;padding-left:6px;"); row.addWidget(label)
        row.addStretch(1)
        for text, tip, callback in [("−", "缩小", lambda: self._canvas.set_zoom(self._canvas.zoom() - .1)), ("⌖", "适应窗口", self._canvas_fit_placeholder), ("＋", "放大", lambda: self._canvas.set_zoom(self._canvas.zoom() + .1))]:
            button = QtWidgets.QToolButton(); button.setText(text); button.setToolTip(tip); button.setFixedSize(28, 28); button.setStyleSheet("QToolButton{border:1px solid #c3d0d4;border-radius:4px;background:white;color:#53656c;}")
            if tip == "适应窗口": self._fit_button = button
            button.clicked.connect(callback); row.addWidget(button)
        layout.addWidget(tools)
        self._canvas = CanvasView(); self._canvas.control_selected.connect(self._on_canvas_selected); self._canvas.item_drag_started.connect(lambda: self._push_history(silent=True)); self._canvas.item_drag_finished.connect(self._finish_drag); self._canvas.zoom_changed.connect(self._zoom_changed); layout.addWidget(self._canvas, 1)
        footer = QtWidgets.QFrame(); footer.setFixedHeight(42); footer.setStyleSheet("background:#edf2f4;border-top:1px solid #c3d0d4;")
        footer_row = QtWidgets.QHBoxLayout(footer); footer_row.setContentsMargins(14, 0, 14, 0); footer_row.setSpacing(12)
        self._sync_label = QtWidgets.QLabel("● 已连接 PhoneKB"); self._sync_label.setStyleSheet("color:#078b84;font-size:9px;font-weight:800;"); footer_row.addWidget(self._sync_label)
        self._canvas_info = QtWidgets.QLabel("画布 2400 × 1080"); self._canvas_info.setStyleSheet("color:#687980;font-size:9px;"); footer_row.addWidget(self._canvas_info)
        self._component_count = QtWidgets.QLabel("0 个组件"); self._component_count.setStyleSheet("color:#687980;font-size:9px;"); footer_row.addWidget(self._component_count)
        note = QtWidgets.QLabel("无独立字母层"); note.setStyleSheet("color:#687980;font-size:9px;"); footer_row.addWidget(note); footer_row.addStretch(1)
        self._toast_label = QtWidgets.QLabel("单层组件模式"); self._toast_label.setStyleSheet("color:#687980;font-size:9px;"); footer_row.addWidget(self._toast_label)
        self._zoom_label = QtWidgets.QLabel("100%"); self._zoom_label.setStyleSheet("color:#4e636b;font-size:9px;"); footer_row.addWidget(self._zoom_label); layout.addWidget(footer)
        return center

    def _canvas_fit_placeholder(self):
        if hasattr(self, "_canvas"):
            self._canvas.fit_to_window()

    def _wire_library(self):
        self._list_panel.layout_chosen.connect(self._choose_layout)
        self._list_panel.new_layout_requested.connect(self._create_layout)
        self._list_panel.layout_action_requested.connect(self._layout_action)
        self._list_panel.background_changed.connect(self._on_background_changed)
        self._list_panel.save_background_requested.connect(self._save_background_preset)
        self._list_panel.delete_background_requested.connect(self._delete_background_preset)
        self._list_panel.add_control.connect(self._add_control)
        self._list_panel.apply_preset_requested.connect(self._apply_component_preset)
        self._list_panel.preset_action_requested.connect(self._preset_action)

    def _wire_inspector(self):
        self._inspector.control_change_started.connect(self._push_history)
        self._inspector.property_changed.connect(self._on_property_changed)
        self._inspector.duplicate_control_clicked.connect(self._duplicate_control)
        self._inspector.delete_control_clicked.connect(self._delete_control)
        self._inspector.save_preset_requested.connect(self._save_component_preset)
        self._inspector.request_export.connect(self._export_json)

    def refresh(self):
        try:
            self._state = gamepad_layouts_loader.load()
            self._component_presets = gamepad_layouts_loader.load_component_presets().get("presets", [])
            self._background_presets = gamepad_layouts_loader.load_background_presets().get("presets", [])
        except Exception as error:
            log.exception("load gamepad layouts failed"); self.status_message.emit("加载控制布局失败：" + str(error)); return
        self._normalize_state(); self._history.clear(); self._future.clear(); self._dirty = False; self._propagate()

    def _normalize_state(self):
        selected = self._state.get("selectedControlId"); self._state = gamepad_layouts_loader.normalize(self._state); controls = self._active_layout().get("controls", [])
        ids = {item.get("id") for item in controls}; self._state["selectedControlId"] = selected if selected in ids else (controls[0]["id"] if controls else None)

    def _propagate(self):
        self._canvas.set_state(self._state); self._canvas.set_background_presets(self._background_presets); self._canvas.rebuild(); self._canvas.set_selected_control(self._state.get("selectedControlId"))
        self._list_panel.set_data(self._state, self._component_presets, self._background_presets)
        self._inspector.set_state(self._state); self._inspector.set_presets(self._component_presets); self._inspector.set_selected_control(self._state.get("selectedControlId"))
        layout = self._active_layout(); self._layout_title.setText(layout.get("name", "控制布局")); canvas = layout.get("canvas") or {"width":2400,"height":1080}
        self._canvas_tag.setText(f"画布 {self._ratio_label(canvas)}"); self._canvas_info.setText(f"画布 {canvas.get('width',2400)} × {canvas.get('height',1080)}"); self._component_count.setText(str(len(layout.get("controls") or [])) + " 个组件"); self._update_buttons()

    @staticmethod
    def _ratio_label(canvas):
        width, height = int(canvas.get("width", 2400)), int(canvas.get("height", 1080))
        for title, w, h in CANVAS_PRESETS:
            if width * h == height * w:
                return title.split()[-1]
        return f"{width}:{height}"

    def _active_layout(self):
        layouts = self._state.get("layouts") or []; active = self._state.get("activeLayoutId")
        return next((item for item in layouts if item.get("id") == active), layouts[0] if layouts else {})

    def _selected_control(self):
        selected = self._state.get("selectedControlId")
        return next((item for item in self._active_layout().get("controls", []) if item.get("id") == selected), None)

    def _choose_layout(self, layout_id):
        if layout_id == self._state.get("activeLayoutId"):
            return
        self._push_history(); self._state["activeLayoutId"] = layout_id; controls = self._active_layout().get("controls", []); self._state["selectedControlId"] = controls[0]["id"] if controls else None; self._propagate(); self._toast("已切换布局", True)

    def _create_layout(self, template):
        default = "空白横屏布局" if template == "blank" else "双摇杆射击布局"; name, ok = QtWidgets.QInputDialog.getText(self, "新建布局", "布局名称", text=default)
        if not ok or not name.strip():
            return
        self._push_history(); controls = []
        if template == "shooter":
            source = gamepad_layouts_loader._default_data()["layouts"][0]
            for item in source["controls"]:
                if item["id"] in {"left-stick", "right-stick", "abxy"}:
                    control = copy.deepcopy(item); control["id"] = _uid("c"); controls.append(control)
        layout = {"id": _uid("layout"), "name": name.strip(), "icon": "⌁" if template == "shooter" else "▦", "controls": controls, "background": {"id": "mobile-light"}, "canvas": {"width":2400,"height":1080}}
        self._state["layouts"].append(layout); self._state["activeLayoutId"] = layout["id"]; self._state["selectedControlId"] = controls[0]["id"] if controls else None; self._propagate(); self._toast("已创建布局", True)

    def _layout_action(self, action, layout_id):
        layout = next((item for item in self._state.get("layouts", []) if item.get("id") == layout_id), None)
        if not layout:
            return
        if action == "rename":
            name, ok = QtWidgets.QInputDialog.getText(self, "重命名布局", "布局名称", text=layout.get("name", "布局"))
            if ok and name.strip(): self._push_history(); layout["name"] = name.strip(); self._propagate()
        elif action == "duplicate":
            self._push_history(); duplicate = copy.deepcopy(layout); duplicate["id"] = _uid("layout"); duplicate["name"] = layout.get("name", "布局") + " 副本"
            for control in duplicate.get("controls", []): control["id"] = _uid("c")
            self._state["layouts"].append(duplicate); self._state["activeLayoutId"] = duplicate["id"]; self._state["selectedControlId"] = duplicate.get("controls", [{}])[0].get("id") if duplicate.get("controls") else None; self._propagate()
        elif action == "delete":
            if len(self._state.get("layouts", [])) <= 1: self._toast("至少保留一个布局"); return
            if QtWidgets.QMessageBox.question(self, "删除布局", f"删除“{layout.get('name','布局')}”？", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No) != QtWidgets.QMessageBox.Yes: return
            self._push_history(); self._state["layouts"] = [item for item in self._state["layouts"] if item.get("id") != layout_id]
            if self._state.get("activeLayoutId") == layout_id: self._state["activeLayoutId"] = self._state["layouts"][0]["id"]
            controls = self._active_layout().get("controls", []); self._state["selectedControlId"] = controls[0]["id"] if controls else None; self._propagate()

    def _add_control(self, spec):
        if isinstance(spec, str):
            spec = {"type": spec}
        ctype = spec.get("type", "key"); info = TYPE_INFO.get(ctype, TYPE_INFO["key"])
        self._push_history(); layout = self._active_layout(); index = len(layout.get("controls", [])); x, y = 64 + index % 4 * 7, 58 + index % 3 * 8
        control = {"id": _uid("c"), "type": ctype, "label": spec.get("label") or info["label"], "x": x, "y": y, "size": spec.get("size", 100), "opacity": 100, "visible": True, "locked": False, "bindings": copy.deepcopy(spec.get("bindings") or gamepad_layouts_loader._default_bindings(ctype)), "appearance": copy.deepcopy(spec.get("appearance") or {"shape": "pill" if ctype in {"shoulder", "macro"} else "round"})}
        if ctype in {"rightStick", "mouse"}: control["sensitivity"] = 55
        if ctype == "shoulder": control["variant"] = "wide"; control["label"] = spec.get("label") or "L"; control["appearance"].setdefault("fill", "#24abc1"); control["appearance"].setdefault("text", "#ffffff")
        layout.setdefault("controls", []).append(control); self._state["selectedControlId"] = control["id"]; self._canvas.add_control_widget(control); self._canvas.set_selected_control(control["id"]); self._inspector.set_selected_control(control["id"]); self._list_panel.set_data(self._state, self._component_presets, self._background_presets); self._component_count.setText(str(len(layout["controls"])) + " 个组件"); self._toast("已添加" + info["title"], True)

    def _on_background_changed(self, background):
        if isinstance(background, str): background = {"id": background}
        self._push_history(); self._canvas.set_background(background); self._list_panel.set_data(self._state, self._component_presets, self._background_presets); self._toast("已切换背景：" + str(background.get("name") or _theme_for_background(background, self._background_presets).get("title", "背景")), True)

    def _save_background_preset(self):
        name, ok = QtWidgets.QInputDialog.getText(self, "保存背景方案", "背景名称", text=_theme_for_background(self._active_layout().get("background"), self._background_presets).get("title", "背景方案"))
        if not ok or not name.strip(): return
        current = copy.deepcopy(self._active_layout().get("background") or {"id":"mobile-light"}); theme = _theme_for_background(current, self._background_presets)
        item = {"id": _uid("background"), "name": name.strip(), "baseId": current.get("baseId") or current.get("id") or "mobile-light", "kind": theme.get("kind", "mobile-light"), "theme": {field: theme[field] for field in gamepad_layouts_loader._BACKGROUND_THEME_FIELDS if field in theme}}
        gamepad_layouts_loader.save_background_preset(item); self._background_presets = gamepad_layouts_loader.load_background_presets().get("presets", []); self._active_layout()["background"] = copy.deepcopy(item); self._propagate(); self._dirty = True; self._toast("背景已保存到库", True)

    def _delete_background_preset(self, preset_id):
        if QtWidgets.QMessageBox.question(self, "删除背景", "删除这个背景预设？", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No) != QtWidgets.QMessageBox.Yes: return
        if gamepad_layouts_loader.delete_background_preset(preset_id):
            self._background_presets = gamepad_layouts_loader.load_background_presets().get("presets", [])
            for layout in self._state.get("layouts", []):
                if (layout.get("background") or {}).get("id") == preset_id: layout["background"] = {"id":"mobile-light"}
            self._propagate(); self._dirty = True

    def _set_canvas_size(self, width, height):
        self._push_history(); self._active_layout()["canvas"] = {"width": int(width), "height": int(height)}; self._propagate(); self._toast(f"画布已设为 {width} × {height}", True)

    def _custom_canvas_size(self):
        canvas = self._active_layout().get("canvas") or {"width":2400,"height":1080}; width, height, ok = CanvasSizeDialog.get_size(self, canvas.get("width",2400), canvas.get("height",1080))
        if ok: self._set_canvas_size(width, height)

    def _on_property_changed(self):
        control = self._selected_control()
        if control: self._canvas.update_control_visual(control)
        self._list_panel.set_data(self._state, self._component_presets, self._background_presets); self._dirty = True

    def _save_component_preset(self):
        control = self._selected_control()
        if not control: self._toast("请先选择组件"); return
        name, ok = QtWidgets.QInputDialog.getText(self, "保存组件预设", "预设名称", text=control.get("label", "组件"))
        if not ok or not name.strip(): return
        component = copy.deepcopy(control); component.pop("_selected", None); component["x"] = 50; component["y"] = 50
        try:
            gamepad_layouts_loader.save_component_preset({"id": _uid("preset"), "name": name.strip(), "control": component}); self._component_presets = gamepad_layouts_loader.load_component_presets().get("presets", []); self._list_panel.set_data(self._state, self._component_presets, self._background_presets); self._toast("已保存组件预设：" + name.strip(), True)
        except Exception as error:
            log.exception("save component preset failed"); self._toast("预设保存失败：" + str(error))

    def _preset_action(self, action, preset):
        if action == "rename":
            name, ok = QtWidgets.QInputDialog.getText(self, "重命名预设", "预设名称", text=preset.get("name", "预设"))
            if ok and name.strip(): gamepad_layouts_loader.rename_component_preset(preset.get("id"), name.strip())
        elif action == "delete":
            if QtWidgets.QMessageBox.question(self, "删除预设", "删除这个组件预设？", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No) != QtWidgets.QMessageBox.Yes: return
            gamepad_layouts_loader.delete_component_preset(preset.get("id"))
        self._component_presets = gamepad_layouts_loader.load_component_presets().get("presets", []); self._list_panel.set_data(self._state, self._component_presets, self._background_presets)

    def _apply_component_preset(self, preset):
        component = copy.deepcopy(preset.get("control") or {})
        if not component: return
        self._push_history(); index = len(self._active_layout().get("controls", [])); component["id"] = _uid("c"); component["x"] = 62 + index % 3 * 8; component["y"] = 58 + index % 3 * 8; component.pop("_selected", None); self._active_layout().setdefault("controls", []).append(component); self._state["selectedControlId"] = component["id"]; self._propagate(); self._toast("已添加组件预设：" + preset.get("name", "未命名"), True)

    def _duplicate_control(self):
        control = self._selected_control()
        if not control: return
        self._push_history(); duplicate = copy.deepcopy(control); duplicate["id"] = _uid("c"); duplicate["label"] = control.get("label", "组件") + " 副本"; duplicate["x"] = min(95, float(control.get("x", 50)) + 5); duplicate["y"] = min(95, float(control.get("y", 50)) + 5); duplicate.pop("_selected", None); self._active_layout()["controls"].append(duplicate); self._state["selectedControlId"] = duplicate["id"]; self._propagate(); self._toast("已复制组件及绑定", True)

    def _delete_control(self):
        control = self._selected_control()
        if not control: return
        if QtWidgets.QMessageBox.question(self, "删除组件", "删除这个组件？", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No) != QtWidgets.QMessageBox.Yes: return
        self._push_history(); controls = [item for item in self._active_layout().get("controls", []) if item.get("id") != control.get("id")]; self._active_layout()["controls"] = controls; self._state["selectedControlId"] = controls[0]["id"] if controls else None; self._propagate(); self._toast("已删除组件")

    def _on_canvas_selected(self, control_id):
        self._state["selectedControlId"] = control_id or None; self._canvas.set_selected_control(control_id); self._inspector.set_selected_control(control_id)

    def _finish_drag(self):
        self._dirty = True; self._inspector.refresh(); self._update_buttons()

    def _push_history(self, silent=False):
        self._history.append(copy.deepcopy(self._state)); self._history = self._history[-80:]; self._future.clear(); self._dirty = True; self._update_buttons()

    def _undo(self):
        if not self._history: return
        self._future.append(copy.deepcopy(self._state)); self._state = self._history.pop(); self._dirty = True; self._propagate()

    def _redo(self):
        if not self._future: return
        self._history.append(copy.deepcopy(self._state)); self._state = self._future.pop(); self._dirty = True; self._propagate()

    def _update_buttons(self):
        self._undo_btn.setEnabled(bool(self._history)); self._redo_btn.setEnabled(bool(self._future))

    def _save(self):
        selected = self._state.get("selectedControlId")
        try:
            self._state = gamepad_layouts_loader.save(self._state); self._state["selectedControlId"] = selected; self._history.clear(); self._future.clear(); self._dirty = False; self._propagate(); self.status_message.emit("控制布局已保存，已连接手机会收到更新"); self._toast("布局已保存并同步手机", True)
            try:
                import server as _server
                _server.notify_gamepad_layouts_changed()
            except Exception:
                pass
        except Exception as error:
            log.exception("save layout failed"); self._toast("保存失败：" + str(error))

    def _export_json(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "导出当前布局", self._active_layout().get("name", "layout") + ".json", "JSON (*.json)")
        if not path: return
        try:
            with open(path, "w", encoding="utf-8") as target: json.dump(self._active_layout(), target, ensure_ascii=False, indent=2)
            self._toast("布局 JSON 已导出", True)
        except OSError as error: self._toast("导出失败：" + str(error))

    def _open_preview(self):
        if self._preview_dialog is None: self._preview_dialog = PreviewDialog(self)
        self._preview_dialog.set_layout(self._active_layout(), self._background_presets); self._preview_dialog.show(); self._preview_dialog.raise_(); self._preview_dialog.activateWindow()

    def _zoom_changed(self, value):
        self._zoom_label.setText(str(value) + "%")

    def keyPressEvent(self, event):
        if event.matches(QtGui.QKeySequence.Undo): self._undo(); event.accept(); return
        if event.matches(QtGui.QKeySequence.Redo): self._redo(); event.accept(); return
        if event.matches(QtGui.QKeySequence.Save): self._save(); event.accept(); return
        if event.key() in {QtCore.Qt.Key_Delete, QtCore.Qt.Key_Backspace} and self._selected_control(): self._delete_control(); event.accept(); return
        if event.key() == QtCore.Qt.Key_Escape: self.back_requested.emit(); event.accept(); return
        super().keyPressEvent(event)

    def _toast(self, message, good=False):
        self._toast_label.setText(message); self._toast_label.setStyleSheet("color:#078b84;font-size:9px;font-weight:800;" if good else "color:#b43b48;font-size:9px;font-weight:800;")

    def is_dirty(self):
        return self._dirty

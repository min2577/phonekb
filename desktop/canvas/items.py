"""Canvas items: ControlItem (UI 层) + LetterItem (字母层)。

两个 item 都用 QGraphicsItem 基类，共享：
  - 百分比坐标 (0-100)，sceneRect 也是 (0,0,100,100)
  - 数据自描述（持有原始 dict，to_dict() 反向序列化）
  - 拖拽移动 (mouseMoveEvent)
  - 选中边框
  - set_accept_selection() 控制当前 mode 下能不能被选中

ControlItem 额外：
  - 按 type 渲染不同外观（leftStick/dpad/abxy/shoulder/key/mouse/macro）
  - bindings: {slot: keyId}，右键菜单可解除绑定
  - 双击/属性面板可重新绑定到已有字母

LetterItem 额外：
  - 显示 value 文本
  - 大小可独立调整（脱离控件）
  - 锁定开关
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional

from PySide6 import QtCore, QtGui, QtWidgets


# ---------- 共享基类 ----------

class _BaseItem(QtWidgets.QGraphicsObject):
    """画布 item 的公共基类。"""

    info_changed = QtCore.Signal(dict)
    bindings_changed = QtCore.Signal(dict)

    def __init__(self, data: dict, base_size: float = 12.0):
        super().__init__()
        self._data = dict(data)
        self._base_size = base_size  # 100% size 时在 scene 里的边长
        self._accept_selection = True
        self._press_offset = QtCore.QPointF(0, 0)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        # 应用初始位置和缩放
        self.setPos(float(data.get("x", 50)), float(data.get("y", 50)))
        self.setTransformOriginPoint(0, 0)
        self.setScale(float(data.get("size", 100)) / 100.0)

    # ---- 选中控制 ----
    def set_accept_selection(self, accept: bool):
        self._accept_selection = accept
        if not accept and self.isSelected():
            self.setSelected(False)

    def mousePressEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent):
        if not self._accept_selection:
            event.ignore()
            return
        if event.button() == QtCore.Qt.LeftButton:
            self._press_offset = self.pos() - event.scenePos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent):
        if not self._accept_selection:
            event.ignore()
            return
        new_pos = event.scenePos() + self._press_offset
        # 限制在 sceneRect 内 (0-100)
        new_pos.setX(max(0, min(100, new_pos.x())))
        new_pos.setY(max(0, min(100, new_pos.y())))
        # 吸附到 0.5 网格，便于精确调整
        new_pos.setX(round(new_pos.x() * 2) / 2)
        new_pos.setY(round(new_pos.y() * 2) / 2)
        self.setPos(new_pos)
        self._data["x"] = round(new_pos.x(), 3)
        self._data["y"] = round(new_pos.y(), 3)
        super().mouseMoveEvent(event)
        self.info_changed.emit({"id": self._data.get("id"), "x": self._data["x"], "y": self._data["y"]})

    def mouseReleaseEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent):
        super().mouseReleaseEvent(event)

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemSelectedHasChanged:
            self.update()
        return super().itemChange(change, value)

    def paint_selected_ring(self, painter: QtGui.QPainter, half: float):
        if self.isSelected():
            ring = QtGui.QPen(QtGui.QColor("#ffcc00"), 0.4)
            ring.setStyle(QtCore.Qt.DashLine)
            painter.setPen(ring)
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawRect(QtCore.QRectF(-half - 1.5, -half - 1.5, (half + 1.5) * 2, (half + 1.5) * 2))

    def set_size_percent(self, percent: float):
        percent = max(50.0, min(200.0, float(percent)))
        self._data["size"] = round(percent, 2)
        self.setScale(percent / 100.0)
        self.info_changed.emit({"id": self._data.get("id"), "size": self._data["size"]})

    def size_percent(self) -> float:
        return float(self._data.get("size", 100))

    def set_opacity_percent(self, percent: float):
        percent = max(30.0, min(100.0, float(percent)))
        self._data["opacity"] = round(percent, 2)
        self.setOpacity(percent / 100.0)
        self.info_changed.emit({"id": self._data.get("id"), "opacity": self._data["opacity"]})

    def to_dict(self) -> dict:
        return dict(self._data)


# ---------- 字母 item ----------

class LetterItem(_BaseItem):

    KIND = "letter"

    def __init__(self, data: dict):
        super().__init__(data, base_size=6.0)
        # 字母 item 永远正方形，size 决定边长
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)

    def key_id(self) -> str:
        return self._data["id"]

    def set_value(self, value: str):
        self._data["value"] = str(value)[:8]
        self.update()
        self.info_changed.emit({"id": self._data["id"], "value": self._data["value"]})

    def value(self) -> str:
        return self._data.get("value", "?")

    def boundingRect(self) -> QtCore.QRectF:
        h = self._base_size / 2 + 1
        return QtCore.QRectF(-h - 2, -h - 2, (h + 2) * 2, (h + 2) * 2)

    def paint(self, painter: QtGui.QPainter, option, widget=None):
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        h = self._base_size / 2
        # 背景：选中态更亮
        if self.isSelected():
            bg = QtGui.QColor("#ffd54a")
            border = QtGui.QColor("#ff8800")
        else:
            bg = QtGui.QColor("#ffeb3b")
            border = QtGui.QColor("#f9a825")
        painter.setBrush(bg)
        painter.setPen(QtGui.QPen(border, 0.3))
        painter.drawRoundedRect(QtCore.QRectF(-h, -h, h * 2, h * 2), 1.2, 1.2)
        # 文字
        text = self.value() or "?"
        font = QtGui.QFont("Microsoft YaHei UI", max(1, int(h * 0.9)), QtGui.QFont.Bold)
        painter.setFont(font)
        painter.setPen(QtGui.QColor("#222"))
        painter.drawText(QtCore.QRectF(-h, -h, h * 2, h * 2), QtCore.Qt.AlignCenter, text)
        self.paint_selected_ring(painter, h)


# ---------- 控件 item ----------

class ControlItem(_BaseItem):

    KIND = "control"

    def __init__(self, data: dict, available_keys: List[dict]):
        super().__init__(data, base_size=10.0)
        self._available_keys = list(available_keys)
        # 控件默认不缩放，是固定大小（size 只影响视觉大小）
        self._refresh_label()

    def control_id(self) -> str:
        return self._data["id"]

    def control_type(self) -> str:
        return self._data.get("type", "key")

    def bindings(self) -> Dict[str, str]:
        return dict(self._data.get("bindings", {}))

    def bind(self, slot: str, key_id: str):
        self._data.setdefault("bindings", {})[slot] = key_id
        self._refresh_label()
        self.bindings_changed.emit({"id": self._data["id"], "slot": slot, "key_id": key_id})

    def unbind(self, slot: str):
        if slot in self._data.get("bindings", {}):
            del self._data["bindings"][slot]
            self._refresh_label()
            self.bindings_changed.emit({"id": self._data["id"], "slot": slot, "key_id": None})

    def set_label(self, label: str):
        self._data["label"] = str(label)[:16]
        self._refresh_label()
        self.info_changed.emit({"id": self._data["id"], "label": self._data["label"]})

    def label(self) -> str:
        return self._data.get("label", "")

    def _refresh_label(self):
        ctype = self.control_type()
        ctype_label = {
            "leftStick": "摇杆", "rightStick": "视角", "dpad": "方向", "abxy": "ABXY",
            "shoulder": "肩键", "key": "按键", "mouse": "鼠标", "macro": "宏",
        }.get(ctype, "控件")
        text = f"{ctype_label}: {self.label() or '-'}"
        binds = self._data.get("bindings", {})
        if binds:
            text += "\n" + ", ".join(f"{slot}→{kid.split('-', 1)[-1]}" for slot, kid in binds.items())
        self._display_text = text

    # ---- 绘制 ----

    def boundingRect(self) -> QtCore.QRectF:
        ctype = self.control_type()
        if ctype in ("leftStick", "rightStick", "dpad", "abxy"):
            r = self._base_size
        elif ctype == "shoulder":
            r = self._base_size * 0.7
        else:
            r = self._base_size * 0.8
        return QtCore.QRectF(-r - 2, -r - 2, (r + 2) * 2, (r + 2) * 2)

    def paint(self, painter: QtGui.QPainter, option, widget=None):
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        ctype = self.control_type()

        # 选中态配色更亮
        if self.isSelected():
            main_color = QtGui.QColor("#42a5f5")
            border_color = QtGui.QColor("#1565c0")
            text_color = QtGui.QColor("white")
        else:
            main_color = QtGui.QColor("#37474f")
            border_color = QtGui.QColor("#90a4ae")
            text_color = QtGui.QColor("white")

        if ctype == "leftStick":
            self._paint_stick(painter, main_color, border_color, text_color, with_arrows=True)
        elif ctype == "rightStick":
            self._paint_stick(painter, main_color, border_color, text_color, with_arrows=False)
        elif ctype == "dpad":
            self._paint_dpad(painter, main_color, border_color, text_color)
        elif ctype == "abxy":
            self._paint_abxy(painter, main_color, border_color, text_color)
        elif ctype == "shoulder":
            self._paint_shoulder(painter, main_color, border_color, text_color)
        elif ctype == "mouse":
            self._paint_mouse(painter, main_color, border_color, text_color)
        elif ctype == "macro":
            self._paint_macro(painter, main_color, border_color, text_color)
        else:
            self._paint_key(painter, main_color, border_color, text_color)

        if ctype in ("leftStick", "rightStick", "dpad", "abxy"):
            h = self._base_size
            self.paint_selected_ring(painter, h)
        else:
            h = self._base_size * 0.7
            self.paint_selected_ring(painter, h)

    def _paint_stick(self, painter, main, border, text, with_arrows: bool):
        r = self._base_size
        # 外圈
        painter.setBrush(main)
        painter.setPen(QtGui.QPen(border, 0.3))
        painter.drawEllipse(QtCore.QPointF(0, 0), r, r)
        # 内圈
        inner = QtGui.QColor(main)
        inner.setAlpha(180)
        painter.setBrush(inner)
        painter.drawEllipse(QtCore.QPointF(0, 0), r * 0.55, r * 0.55)
        # 中心点
        painter.setBrush(QtGui.QColor("#fff"))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawEllipse(QtCore.QPointF(0, 0), r * 0.12, r * 0.12)
        # 文字
        font = QtGui.QFont("Microsoft YaHei UI", max(1, int(r * 0.22)))
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(text)
        painter.drawText(QtCore.QRectF(-r, r * 0.5, r * 2, r * 0.4), QtCore.Qt.AlignCenter, self.label() or ("L" if with_arrows else "R"))

    def _paint_dpad(self, painter, main, border, text):
        r = self._base_size * 0.85
        arm = r * 0.4
        painter.setBrush(main)
        painter.setPen(QtGui.QPen(border, 0.3))
        path = QtGui.QPainterPath()
        path.addRect(QtCore.QRectF(-arm, -r, arm * 2, r * 2))
        path.addRect(QtCore.QRectF(-r, -arm, r * 2, arm * 2))
        painter.drawPath(path)
        painter.setPen(text)
        font = QtGui.QFont("Arial", max(1, int(arm * 0.7)), QtGui.QFont.Bold)
        painter.setFont(font)
        painter.drawText(QtCore.QPointF(0, -r * 0.55), QtCore.Qt.AlignCenter, "▲")
        painter.drawText(QtCore.QPointF(0, r * 0.75), QtCore.Qt.AlignCenter, "▼")
        painter.drawText(QtCore.QPointF(-r * 0.7, 0.3), QtCore.Qt.AlignCenter, "◀")
        painter.drawText(QtCore.QPointF(r * 0.55, 0.3), QtCore.Qt.AlignCenter, "▶")
        font2 = QtGui.QFont("Microsoft YaHei UI", max(1, int(arm * 0.4)))
        painter.setFont(font2)
        painter.drawText(QtCore.QPointF(0, -r * 0.1), self.label() or "")

    def _paint_abxy(self, painter, main, border, text):
        r = self._base_size * 0.85
        painter.setBrush(main)
        painter.setPen(QtGui.QPen(border, 0.3))
        painter.drawEllipse(QtCore.QPointF(0, 0), r, r)
        btn_r = r * 0.28
        font = QtGui.QFont("Arial", max(1, int(btn_r * 1.2)), QtGui.QFont.Bold)
        painter.setFont(font)
        positions = [
            (0, -r * 0.55, "X"),     # 上 X
            (r * 0.55, 0, "B"),      # 右 B
            (0, r * 0.55, "A"),      # 下 A
            (-r * 0.55, 0, "Y"),     # 左 Y
        ]
        painter.setPen(text)
        for x, y, ch in positions:
            painter.drawText(QtCore.QPointF(x - btn_r, y + btn_r * 0.4), ch)

    def _paint_shoulder(self, painter, main, border, text):
        w, h = self._base_size * 1.3, self._base_size * 0.6
        painter.setBrush(main)
        painter.setPen(QtGui.QPen(border, 0.3))
        painter.drawRoundedRect(QtCore.QRectF(-w / 2, -h / 2, w, h), 1.0, 1.0)
        font = QtGui.QFont("Microsoft YaHei UI", max(1, int(h * 0.55)), QtGui.QFont.Bold)
        painter.setFont(font)
        painter.setPen(text)
        painter.drawText(QtCore.QRectF(-w / 2, -h / 2, w, h), QtCore.Qt.AlignCenter, self.label() or "L")

    def _paint_key(self, painter, main, border, text):
        s = self._base_size * 0.7
        painter.setBrush(main)
        painter.setPen(QtGui.QPen(border, 0.3))
        painter.drawRoundedRect(QtCore.QRectF(-s, -s, s * 2, s * 2), 1.2, 1.2)
        font = QtGui.QFont("Microsoft YaHei UI", max(1, int(s * 0.45)), QtGui.QFont.Bold)
        painter.setFont(font)
        painter.setPen(text)
        painter.drawText(QtCore.QRectF(-s, -s, s * 2, s * 2), QtCore.Qt.AlignCenter, self.label() or "K")

    def _paint_mouse(self, painter, main, border, text):
        s = self._base_size * 0.7
        painter.setBrush(main)
        painter.setPen(QtGui.QPen(border, 0.3))
        painter.drawRoundedRect(QtCore.QRectF(-s, -s, s * 2, s * 2), 1.2, 1.2)
        painter.setPen(text)
        font = QtGui.QFont("Arial", max(1, int(s * 0.7)), QtGui.QFont.Bold)
        painter.setFont(font)
        painter.drawText(QtCore.QRectF(-s, -s, s * 2, s * 2), QtCore.Qt.AlignCenter, "🖱")

    def _paint_macro(self, painter, main, border, text):
        s = self._base_size * 0.7
        painter.setBrush(main)
        painter.setPen(QtGui.QPen(border, 0.3))
        painter.drawRoundedRect(QtCore.QRectF(-s, -s, s * 2, s * 2), 1.2, 1.2)
        painter.setPen(text)
        font = QtGui.QFont("Arial", max(1, int(s * 0.7)), QtGui.QFont.Bold)
        painter.setFont(font)
        painter.drawText(QtCore.QRectF(-s, -s, s * 2, s * 2), QtCore.Qt.AlignCenter, "M")
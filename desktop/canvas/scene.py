"""GamepadScene - 手柄布局编辑器的双层画布。

数据模型继承自 gamepad_layouts_loader：
  - 控件（controls）：UI 层，可点击/拖拽区域，每个控件有 type/label/x/y/size/opacity/bindings
  - 字母（keys）：字母层，独立画布对象，每个字母有 value/x/y/size/opacity
  - 绑定：control.bindings[slot] = keyId（例如左摇杆.up -> key-w）

坐标全部用 0-100 百分比。QGraphicsScene 的 sceneRect 设为 (0, 0, 100, 100)，
view 用 Qt.KeepAspectRatio 缩放，保证手机横屏尺寸变化时控件位置不变形。
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional

from PySide6 import QtCore, QtGui, QtWidgets

from canvas.items import ControlItem, LetterItem


# 编辑模式常量
MODE_UI = "ui"          # 只能选中/拖动控件（UI 层）
MODE_LETTER = "letter"  # 只能选中/拖动字母（字母层）


class GamepadScene(QtWidgets.QGraphicsScene):
    """手柄布局双层画布场景。"""

    selection_info_changed = QtCore.Signal(dict)
    layout_modified = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(0, 0, 100, 100, parent)
        self._mode = MODE_UI
        self._active_layout: Optional[dict] = None
        self._control_items: Dict[str, ControlItem] = {}
        self._letter_items: Dict[str, LetterItem] = {}

        self.setBackgroundBrush(QtGui.QBrush(QtGui.QColor("#1f2330")))
        # 10% 网格
        self._draw_grid()

    # ---------- 公开接口 ----------

    def set_mode(self, mode: str):
        if mode not in (MODE_UI, MODE_LETTER):
            return
        if mode == self._mode:
            return
        self._mode = mode
        for item in self._control_items.values():
            item.set_accept_selection(mode == MODE_UI)
            if mode == MODE_LETTER:
                item.setOpacity(0.35)
            else:
                item.setOpacity(item._data.get("opacity", 100) / 100.0)
        for item in self._letter_items.values():
            item.set_accept_selection(mode == MODE_LETTER)
            if mode == MODE_UI:
                item.setOpacity(0.35)
            else:
                item.setOpacity(item._data.get("opacity", 100) / 100.0)
        self.clearSelection()
        self.selection_info_changed.emit({"mode": mode, "kind": None, "id": None})

    def load_layout(self, layout: dict):
        """用一份 layout 数据（包含 keys + controls）重建画布。"""
        self._active_layout = layout
        self.clear()
        self._control_items.clear()
        self._letter_items.clear()
        self._draw_grid()

        # 先创建字母（z 较低，但 mode=UI 时会被半透明）
        for key_data in layout.get("keys", []):
            item = LetterItem(key_data)
            item.set_accept_selection(self._mode == MODE_LETTER)
            item.info_changed.connect(self._on_item_info_changed)
            item.bindings_changed.connect(self._on_item_bindings_changed)
            self.addItem(item)
            self._letter_items[key_data["id"]] = item

        # 再创建控件（z 较高）
        for control_data in layout.get("controls", []):
            item = ControlItem(control_data, available_keys=layout.get("keys", []))
            item.set_accept_selection(self._mode == MODE_UI)
            item.info_changed.connect(self._on_item_info_changed)
            item.bindings_changed.connect(self._on_item_bindings_changed)
            self.addItem(item)
            self._control_items[control_data["id"]] = item

        self._apply_mode_opacity()
        self.selection_info_changed.emit({"mode": self._mode, "kind": None, "id": None})

    def current_layout(self) -> dict:
        """从画布反向序列化回 layout dict（用于保存）。"""
        if not self._active_layout:
            return {"keys": [], "controls": []}
        keys = [item.to_dict() for item in self._letter_items.values()]
        controls = [item.to_dict() for item in self._control_items.values()]
        return {
            "id": self._active_layout.get("id"),
            "name": self._active_layout.get("name"),
            "icon": self._active_layout.get("icon"),
            "keys": keys,
            "controls": controls,
        }

    def add_letter(self, value: str = "?") -> str:
        """新增一个独立字母到画布中央，返回新字母 id。"""
        if not self._active_layout:
            return ""
        existing_ids = {k["id"] for k in self._active_layout.get("keys", [])}
        idx = 1
        while f"key-{idx}" in existing_ids:
            idx += 1
        new_id = f"key-{idx}"
        key_data = {
            "id": new_id,
            "value": value,
            "x": 50.0,
            "y": 50.0,
            "size": 100.0,
            "opacity": 100.0,
            "locked": False,
        }
        item = LetterItem(key_data)
        item.set_accept_selection(self._mode == MODE_LETTER)
        item.info_changed.connect(self._on_item_info_changed)
        item.bindings_changed.connect(self._on_item_bindings_changed)
        self.addItem(item)
        self._letter_items[new_id] = item
        self._active_layout.setdefault("keys", []).append(key_data)
        self.layout_modified.emit()
        self._apply_mode_opacity()
        item.setSelected(True)
        return new_id

    def add_control(self, control_type: str = "key", label: str = "按键") -> str:
        """新增一个独立控件（默认 key 类型）到画布中央，返回新 id。"""
        if not self._active_layout:
            return ""
        existing_ids = {c["id"] for c in self._active_layout.get("controls", [])}
        idx = 1
        while f"control-{idx}" in existing_ids:
            idx += 1
        new_id = f"control-{idx}"
        control_data = {
            "id": new_id,
            "type": control_type,
            "label": label,
            "x": 50.0,
            "y": 50.0,
            "size": 100.0,
            "opacity": 100.0,
            "locked": False,
            "bindings": {},
        }
        item = ControlItem(control_data, available_keys=self._active_layout.get("keys", []))
        item.set_accept_selection(self._mode == MODE_UI)
        item.info_changed.connect(self._on_item_info_changed)
        item.bindings_changed.connect(self._on_item_bindings_changed)
        self.addItem(item)
        self._control_items[new_id] = item
        self._active_layout.setdefault("controls", []).append(control_data)
        self.layout_modified.emit()
        self._apply_mode_opacity()
        item.setSelected(True)
        return new_id

    def delete_selected(self) -> bool:
        """删除当前选中的 item（控件或字母）。"""
        deleted = False
        for item in list(self.selectedItems()):
            if isinstance(item, LetterItem):
                self._remove_letter(item.key_id())
            elif isinstance(item, ControlItem):
                self._remove_control(item.control_id())
            deleted = True
        return deleted

    # ---------- 内部 ----------

    def _remove_letter(self, key_id: str):
        item = self._letter_items.pop(key_id, None)
        if not item:
            return
        # 解除所有指向该字母的 bindings
        for control in self._control_items.values():
            for slot, bound_id in list(control.bindings().items()):
                if bound_id == key_id:
                    control.unbind(slot)
        if self._active_layout:
            self._active_layout["keys"] = [k for k in self._active_layout.get("keys", []) if k["id"] != key_id]
        self.removeItem(item)
        self.layout_modified.emit()
        self.selection_info_changed.emit({"mode": self._mode, "kind": None, "id": None})

    def _remove_control(self, control_id: str):
        item = self._control_items.pop(control_id, None)
        if not item:
            return
        if self._active_layout:
            self._active_layout["controls"] = [c for c in self._active_layout.get("controls", []) if c["id"] != control_id]
        self.removeItem(item)
        self.layout_modified.emit()
        self.selection_info_changed.emit({"mode": self._mode, "kind": None, "id": None})

    def _apply_mode_opacity(self):
        """根据当前 mode 控制非活动层的透明度。"""
        for item in self._control_items.values():
            if self._mode == MODE_UI:
                item.setOpacity(item._data.get("opacity", 100) / 100.0)
            else:
                item.setOpacity(0.35)
        for item in self._letter_items.values():
            if self._mode == MODE_LETTER:
                item.setOpacity(item._data.get("opacity", 100) / 100.0)
            else:
                item.setOpacity(0.35)

    def _on_item_info_changed(self, _info: dict):
        self.layout_modified.emit()
        # 把当前选中信息推出去刷新属性面板
        for item in self.selectedItems():
            if isinstance(item, ControlItem):
                self.selection_info_changed.emit({"mode": self._mode, "kind": "control", "id": item.control_id()})
                return
            if isinstance(item, LetterItem):
                self.selection_info_changed.emit({"mode": self._mode, "kind": "letter", "id": item.key_id()})
                return

    def _on_item_bindings_changed(self, _info: dict):
        self.layout_modified.emit()

    def _draw_grid(self):
        pen = QtGui.QPen(QtGui.QColor(255, 255, 255, 18))
        pen.setWidthF(0)
        for i in range(0, 101, 10):
            self.addLine(i, 0, i, 100, pen)
            self.addLine(0, i, 100, i, pen)
        # 中线略亮
        mid_pen = QtGui.QPen(QtGui.QColor(255, 255, 255, 36))
        self.addLine(50, 0, 50, 100, mid_pen)
        self.addLine(0, 50, 100, 50, mid_pen)
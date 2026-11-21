"""Desktop macro recorder and side-by-side timing comparison page."""
from __future__ import annotations

import asyncio
import threading

from PySide6 import QtCore, QtGui, QtWidgets

import macro_library
import server
import layouts_loader
import acer_mousehub
from input_recorder import InputRecorder
from global_hotkey import GlobalHotkey, VK_F8


class MacroComparePage(QtWidgets.QWidget):
    status_message = QtCore.Signal(str)
    playback_finished = QtCore.Signal(bool, str)
    recording_stop_requested = QtCore.Signal()
    hotkey_toggle_requested = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("macroComparePage")
        self._recordings = []
        self._recorder = None
        self._record_started_at = None
        self._elapsed_timer = QtCore.QTimer(self)
        self._elapsed_timer.timeout.connect(self._update_recording_elapsed)
        self._playback_timer = QtCore.QTimer(self)
        self._playback_timer.timeout.connect(self._playback_tick)
        self._playback_countdown = 0
        self._pending_playback = None
        self._hotkey = GlobalHotkey(self._toggle_recording_from_hotkey, VK_F8)
        self._hotkey.start()
        if not self._hotkey.wait_ready():
            self.status_message.emit("F8 快捷键注册失败，可能已被其他软件占用")
        self.playback_finished.connect(self._on_playback_finished)
        self.recording_stop_requested.connect(self._stop_recording)
        self.hotkey_toggle_requested.connect(self._toggle_recording_ui)
        self._build_ui()
        self._ensure_requested_macro_imported()
        self.refresh()

    def _build_ui(self):
        self.setStyleSheet("""
            QWidget#macroComparePage { background: #f4f5f7; color: #202832; font-family: "Microsoft YaHei UI"; }
            QFrame#toolbar, QFrame#summary { background: #ffffff; border: 1px solid #d9dee5; border-radius: 6px; }
            QPushButton { min-height: 34px; padding: 0 14px; border: 1px solid #c8d0d9; border-radius: 5px; background: #ffffff; }
            QPushButton:hover { background: #f0f5f7; }
            QPushButton#recordButton { color: #ffffff; background: #d14343; border-color: #d14343; font-weight: 600; }
            QPushButton#stopButton { color: #ffffff; background: #263746; border-color: #263746; font-weight: 600; }
            QPushButton#testButton { color: #ffffff; background: #087f8c; border-color: #087f8c; }
            QLineEdit { min-height: 34px; padding: 0 10px; border: 1px solid #c8d0d9; border-radius: 5px; background: #ffffff; }
            QListWidget, QTableWidget { background: #ffffff; border: 1px solid #d9dee5; border-radius: 5px; gridline-color: #e5e9ee; }
            QListWidget::item { min-height: 42px; padding: 4px 8px; }
            QListWidget::item:selected { background: #dceff1; color: #153c43; }
            QHeaderView::section { background: #eef2f4; color: #33434d; border: none; border-right: 1px solid #d9dee5; border-bottom: 1px solid #d9dee5; padding: 8px; font-weight: 600; }
        """)
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(12)

        title_row = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("宏录制与对比")
        font = title.font(); font.setPointSize(18); font.setBold(True); title.setFont(font)
        title_row.addWidget(title)
        title_row.addStretch()
        self._record_state = QtWidgets.QLabel("未录制")
        self._record_state.setStyleSheet("color:#60717c;font-weight:600;")
        title_row.addWidget(self._record_state)
        root.addLayout(title_row)

        toolbar = QtWidgets.QFrame(objectName="toolbar")
        toolbar_layout = QtWidgets.QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(12, 10, 12, 10)
        self._name_input = QtWidgets.QLineEdit()
        self._name_input.setPlaceholderText("录制名称，例如：连招版本 A")
        self._name_input.setMaximumWidth(310)
        toolbar_layout.addWidget(self._name_input)
        self._record_button = QtWidgets.QPushButton("开始录制", objectName="recordButton")
        self._stop_button = QtWidgets.QPushButton("停止并保存", objectName="stopButton")
        self._stop_button.setEnabled(False)
        self._test_button = QtWidgets.QPushButton("测试选中方案", objectName="testButton")
        self._acer_button = QtWidgets.QPushButton("导出并绑定鼠标侧键")
        self._record_button.clicked.connect(self._start_recording)
        self._stop_button.clicked.connect(self._stop_recording)
        self._test_button.clicked.connect(self._test_selected)
        self._acer_button.clicked.connect(self._export_selected_to_acer)
        toolbar_layout.addWidget(self._record_button)
        toolbar_layout.addWidget(self._stop_button)
        toolbar_layout.addSpacing(8)
        toolbar_layout.addWidget(self._test_button)
        toolbar_layout.addWidget(self._acer_button)
        toolbar_layout.addStretch()
        help_label = QtWidgets.QLabel("F8：开始/停止录制 · 不记录鼠标移动")
        help_label.setStyleSheet("color:#71808a;")
        toolbar_layout.addWidget(help_label)
        root.addWidget(toolbar)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        library_panel = QtWidgets.QWidget()
        library_layout = QtWidgets.QVBoxLayout(library_panel)
        library_layout.setContentsMargins(0, 0, 0, 0)
        library_title = QtWidgets.QLabel("录制方案  ·  勾选 2-4 个进行对比")
        library_title.setStyleSheet("font-weight:600;")
        library_layout.addWidget(library_title)
        self._list = QtWidgets.QListWidget()
        self._list.currentItemChanged.connect(lambda *_: self._update_comparison())
        self._list.itemChanged.connect(self._on_item_checked)
        library_layout.addWidget(self._list, 1)
        actions = QtWidgets.QGridLayout()
        rename = QtWidgets.QPushButton("重命名")
        delete = QtWidgets.QPushButton("删除选中")
        duplicate = QtWidgets.QPushButton("复制")
        rename.clicked.connect(self._rename_selected)
        delete.clicked.connect(self._delete_checked_or_selected)
        duplicate.clicked.connect(self._duplicate_selected)
        actions.addWidget(rename, 0, 0); actions.addWidget(duplicate, 0, 1); actions.addWidget(delete, 1, 0)
        import_phone = QtWidgets.QPushButton("导入手机宏")
        import_phone.clicked.connect(self._import_phone_macro)
        actions.addWidget(import_phone, 1, 1)
        library_layout.addLayout(actions)
        splitter.addWidget(library_panel)

        compare_panel = QtWidgets.QWidget()
        compare_layout = QtWidgets.QVBoxLayout(compare_panel)
        compare_layout.setContentsMargins(0, 0, 0, 0)
        self._summary = QtWidgets.QLabel("选择一个方案查看统计；勾选多个方案进行对比")
        self._summary.setWordWrap(True)
        self._summary.setMinimumHeight(52)
        self._summary.setStyleSheet("background:#ffffff;border:1px solid #d9dee5;border-radius:5px;padding:8px 12px;color:#40515b;")
        compare_layout.addWidget(self._summary)
        self._table = QtWidgets.QTableWidget()
        self._table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        compare_layout.addWidget(self._table, 1)
        edit_actions = QtWidgets.QHBoxLayout()
        delete_action = QtWidgets.QPushButton("删除选中动作")
        edit_delay = QtWidgets.QPushButton("修改选中间隔")
        delete_action.clicked.connect(self._delete_selected_action)
        edit_delay.clicked.connect(self._edit_selected_delay)
        edit_actions.addWidget(delete_action)
        edit_actions.addWidget(edit_delay)
        edit_actions.addStretch()
        compare_layout.addLayout(edit_actions)
        splitter.addWidget(compare_panel)
        splitter.setSizes([310, 800])
        root.addWidget(splitter, 1)

    def refresh(self):
        checked = {self._item_id(item) for item in self._checked_items()}
        current_id = self._item_id(self._list.currentItem())
        self._recordings = macro_library.load()
        self._list.blockSignals(True)
        self._list.clear()
        for recording in self._recordings:
            stats = macro_library.statistics(recording["macro"])
            item = QtWidgets.QListWidgetItem(f'{recording["name"]}\n{stats["actions"]} 个动作  ·  {stats["duration_ms"]} ms')
            item.setData(QtCore.Qt.UserRole, recording["id"])
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.Checked if recording["id"] in checked else QtCore.Qt.Unchecked)
            self._list.addItem(item)
            if recording["id"] == current_id:
                self._list.setCurrentItem(item)
        self._list.blockSignals(False)
        if self._list.count() and not self._list.currentItem():
            self._list.setCurrentRow(0)
        self._update_comparison()

    def _start_recording(self):
        if self._recorder:
            return
        recorder = InputRecorder()
        ok, error = recorder.start()
        if not ok:
            QtWidgets.QMessageBox.warning(self, "无法开始录制", error or "键盘鼠标监听启动失败")
            return
        self._recorder = recorder
        self._record_started_at = QtCore.QElapsedTimer()
        self._record_started_at.start()
        self._elapsed_timer.start(100)
        self._record_button.setEnabled(False)
        self._stop_button.setEnabled(True)
        self._record_state.setText("录制中 · 0.0 秒")
        self.status_message.emit("录制已开始，请切换到游戏完成操作")

    def _toggle_recording_from_hotkey(self):
        self.hotkey_toggle_requested.emit()

    def _toggle_recording_ui(self):
        if self._recorder:
            self._stop_recording()
        else:
            self._start_recording()

    def _stop_recording(self):
        if not self._recorder:
            return
        macro = self._recorder.stop()
        self._recorder = None
        self._elapsed_timer.stop()
        self._record_button.setEnabled(True)
        self._stop_button.setEnabled(False)
        action_count = len(macro_library.action_rows(macro))
        self._record_state.setText(f"录制完成 · {action_count} 个动作")
        if action_count == 0:
            QtWidgets.QMessageBox.information(self, "没有录到操作", "本次没有记录到键盘或鼠标操作，不会保存空方案。")
            return
        default_name = f"录制 {len(self._recordings) + 1}"
        name = self._name_input.text().strip() or default_name
        recording = macro_library.create(name, macro)
        self._recordings.insert(0, recording)
        macro_library.save(self._recordings)
        self._name_input.clear()
        self.refresh()
        self._select_id(recording["id"])
        self.status_message.emit(f"已保存：{name}")

    def _update_recording_elapsed(self):
        if self._record_started_at:
            self._record_state.setText(f"录制中 · {self._record_started_at.elapsed() / 1000:.1f} 秒")

    def _on_item_checked(self, changed_item):
        checked = self._checked_items()
        if len(checked) > 4:
            self._list.blockSignals(True)
            changed_item.setCheckState(QtCore.Qt.Unchecked)
            self._list.blockSignals(False)
            self.status_message.emit("最多同时对比 4 个方案")
        self._update_comparison()

    def _update_summary(self):
        recording = self._selected_recording()
        if not recording:
            self._summary.setText("选择一个方案查看统计；勾选多个方案进行对比")
            return
        stats = macro_library.statistics(recording["macro"])
        self._summary.setText(
            f'{recording["name"]}：{stats["actions"]} 个动作，合计 {stats["duration_ms"]} ms，'
            f'平均间隔 {stats["average_ms"]} ms，最长间隔 {stats["maximum_ms"]} ms'
        )

    def _update_comparison(self):
        selected = [self._recording_by_id(self._item_id(item)) for item in self._checked_items()]
        selected = [item for item in selected if item]
        if not selected:
            current = self._selected_recording()
            selected = [current] if current else []
        rows_by_recording = [macro_library.action_rows(item["macro"]) for item in selected]
        aligned_rows = self._align_action_rows(rows_by_recording)
        self._display_recordings = selected
        self._aligned_rows = aligned_rows
        row_count = len(aligned_rows)
        self._table.clear()
        self._table.setRowCount(row_count)
        self._table.setColumnCount(1 + len(selected) * 2)
        headers = ["步骤"]
        for item in selected:
            headers.extend([item["name"], "间隔"])
        self._table.setHorizontalHeaderLabels(headers)
        for row_index, aligned in enumerate(aligned_rows):
            number = QtWidgets.QTableWidgetItem(str(row_index + 1))
            number.setTextAlignment(QtCore.Qt.AlignCenter)
            self._table.setItem(row_index, 0, number)
            row_actions = []
            for scheme_index, row in enumerate(aligned):
                action = row["action"] if row else "—"
                delay = f'{row["delay_ms"]} ms' if row else "—"
                row_actions.append(action)
                action_item = QtWidgets.QTableWidgetItem(action)
                action_item.setToolTip(action)
                delay_item = QtWidgets.QTableWidgetItem(delay)
                delay_item.setTextAlignment(QtCore.Qt.AlignCenter)
                self._table.setItem(row_index, 1 + scheme_index * 2, action_item)
                self._table.setItem(row_index, 2 + scheme_index * 2, delay_item)
            mismatch = len(set(row_actions)) > 1
            if mismatch:
                for scheme_index in range(len(selected)):
                    self._table.item(row_index, 1 + scheme_index * 2).setBackground(QtGui.QColor("#fde1dd"))
                self._table.item(row_index, 0).setToolTip("动作不同：请按动作名称对齐，而不是只看步骤序号")
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        for column in range(1, self._table.columnCount()):
            header.setSectionResizeMode(column, QtWidgets.QHeaderView.Stretch if column % 2 else QtWidgets.QHeaderView.ResizeToContents)
        self._update_summary()

    def _ensure_requested_macro_imported(self):
        if any(item.get("name") == "手机方案 · 感觉" for item in macro_library.load()):
            return
        found = self._find_phone_macros()
        macro = next((item for item in found if item["layout"] == "快捷键方案 1" and item["label"] == "感觉"), None)
        if not macro:
            return
        items = macro_library.load()
        items.insert(0, macro_library.create("手机方案 · 感觉", macro["macro"]))
        macro_library.save(items)

    def _find_phone_macros(self):
        result = []
        data = layouts_loader.load()
        for layout in data.get("layouts", []):
            for page in layout.get("pages", []):
                for slot in page.get("slots", []):
                    key = slot.get("key") if isinstance(slot, dict) else None
                    if isinstance(key, dict) and key.get("type") == "macro" and isinstance(key.get("macro"), dict):
                        result.append({
                            "layout": str(layout.get("name") or layout.get("id") or "方案"),
                            "label": str(key.get("label") or "未命名宏"),
                            "macro": key["macro"],
                        })
        return result

    def _import_phone_macro(self):
        macros = self._find_phone_macros()
        if not macros:
            self.status_message.emit("手机快捷键方案中没有宏")
            return
        labels = [item["layout"] + " / " + item["label"] for item in macros]
        choice, ok = QtWidgets.QInputDialog.getItem(self, "导入手机宏", "选择宏", labels, 0, False)
        if not ok:
            return
        index = labels.index(choice)
        source = macros[index]
        recording = macro_library.create("手机方案 · " + source["label"], source["macro"])
        self._recordings.insert(0, recording)
        macro_library.save(self._recordings)
        self.refresh()
        self._select_id(recording["id"])
        self.status_message.emit("已导入：" + choice)

    def _selected_action_context(self):
        row_index = self._table.currentRow()
        if row_index < 0 or row_index >= len(getattr(self, "_aligned_rows", [])):
            self.status_message.emit("请先在右侧表格选择一个动作")
            return None
        recording = self._selected_recording()
        displayed = getattr(self, "_display_recordings", [])
        try:
            scheme_index = next(index for index, item in enumerate(displayed) if item["id"] == recording["id"])
        except (StopIteration, TypeError):
            self.status_message.emit("请先选择要编辑的方案")
            return None
        row = self._aligned_rows[row_index][scheme_index]
        if not row:
            self.status_message.emit("这个方案在该行没有动作")
            return None
        return recording, row

    def _delete_selected_action(self):
        context = self._selected_action_context()
        if not context:
            return
        recording, row = context
        remove_indexes = set(row.get("wait_indexes", []))
        remove_indexes.add(row["step_index"])
        steps = recording["macro"]["steps"]
        recording["macro"]["steps"] = [step for index, step in enumerate(steps) if index not in remove_indexes]
        macro_library.save(self._recordings)
        self.refresh()
        self._select_id(recording["id"])
        self.status_message.emit("已删除动作：" + row["action"])

    def _edit_selected_delay(self):
        context = self._selected_action_context()
        if not context:
            return
        recording, row = context
        if row["step_index"] == 0:
            self.status_message.emit("第一个动作之前没有间隔")
            return
        value, ok = QtWidgets.QInputDialog.getInt(
            self, "修改间隔", "该动作距离上一个动作的间隔（毫秒）",
            int(row.get("delay_ms", 0)), 0, 60000, 1,
        )
        if not ok:
            return
        steps = recording["macro"]["steps"]
        wait_indexes = list(row.get("wait_indexes", []))
        if wait_indexes:
            first = wait_indexes[0]
            steps[first] = {"type": "wait_ms", "value": value}
            for index in reversed(wait_indexes[1:]):
                del steps[index]
        else:
            steps.insert(row["step_index"], {"type": "wait_ms", "value": value})
        macro_library.save(self._recordings)
        self.refresh()
        self._select_id(recording["id"])
        self.status_message.emit(f"间隔已修改为 {value} ms")

    @staticmethod
    def _align_action_rows(rows_by_recording):
        """Align rows by action text instead of blindly matching row numbers."""
        if not rows_by_recording:
            return []
        reference = rows_by_recording[0]
        cursors = [0] * len(rows_by_recording)
        aligned = []
        for ref in reference:
            row = [ref]
            for scheme_index in range(1, len(rows_by_recording)):
                rows = rows_by_recording[scheme_index]
                match = None
                for index in range(cursors[scheme_index], len(rows)):
                    if MacroComparePage._action_identity(rows[index]["action"]) == MacroComparePage._action_identity(ref["action"]):
                        match = index
                        break
                if match is None:
                    row.append(None)
                else:
                    for extra_index in range(cursors[scheme_index], match):
                        extra_row = [None] * len(rows_by_recording)
                        extra_row[scheme_index] = dict(rows[extra_index], action="新增：" + rows[extra_index]["action"])
                        aligned.append(extra_row)
                    row.append(rows[match])
                    cursors[scheme_index] = match + 1
            aligned.append(row)
        for scheme_index, rows in enumerate(rows_by_recording[1:], 1):
            for index in range(cursors[scheme_index], len(rows)):
                extra_row = [None] * len(rows_by_recording)
                extra_row[scheme_index] = dict(rows[index], action="新增：" + rows[index]["action"])
                aligned.append(extra_row)
        return aligned

    @staticmethod
    def _action_identity(value):
        """Ignore measured tap duration when matching the same physical action."""
        text = str(value or "")
        marker = text.find("（")
        return text[:marker] if marker >= 0 else text

    def _test_selected(self):
        recording = self._selected_recording()
        if not recording:
            self.status_message.emit("请先选择一个方案")
            return
        self._test_button.setEnabled(False)
        self._pending_playback = recording
        self._playback_countdown = 3
        self._test_button.setText("3 秒后执行")
        self.status_message.emit("请在 3 秒内切换到游戏窗口")
        self._playback_timer.start(1000)

    def _export_selected_to_acer(self):
        recording = self._selected_recording()
        if not recording:
            self.status_message.emit("请先选择一个方案")
            return
        if acer_mousehub.is_running():
            QtWidgets.QMessageBox.information(
                self, "请先退出 Acer MouseHub",
                "请从任务栏托盘彻底退出 Acer MouseHub，再点击导出。\n\n"
                "直接关闭窗口可能只是最小化到托盘。",
            )
            return
        try:
            result = acer_mousehub.export_macro(recording["name"], recording["macro"], bind_key_code=3)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "导出失败", str(exc))
            return
        QtWidgets.QMessageBox.information(
            self, "导出完成",
            f'已新建宏“{result["name"]}”，共 {result["events"]} 个事件。\n\n'
            "现在重新打开 Acer MouseHub，在宏管理中检查并绑定到鼠标侧键。",
        )
        self.status_message.emit("已导出到 Acer MouseHub：" + result["name"])

    def _playback_tick(self):
        self._playback_countdown -= 1
        if self._playback_countdown > 0:
            self._test_button.setText(f"{self._playback_countdown} 秒后执行")
            return
        self._playback_timer.stop()
        recording = self._pending_playback
        self._pending_playback = None
        if not recording:
            self._on_playback_finished(False, "方案不存在")
            return
        self._test_button.setText("测试中…")
        macro = recording["macro"]

        def run():
            try:
                asyncio.run(server._execute_macro(object(), macro.get("steps", []), macro.get("interval_ms", 0)))
                self.playback_finished.emit(True, recording["name"])
            except Exception as exc:
                self.playback_finished.emit(False, str(exc))

        threading.Thread(target=run, name="phonekb-macro-test", daemon=True).start()

    def _on_playback_finished(self, ok, message):
        self._test_button.setEnabled(True)
        self._test_button.setText("测试选中方案")
        self.status_message.emit(("测试完成：" if ok else "测试失败：") + message)

    def _rename_selected(self):
        recording = self._selected_recording()
        if not recording:
            return
        name, ok = QtWidgets.QInputDialog.getText(self, "重命名方案", "方案名称", text=recording["name"])
        if ok and name.strip():
            recording["name"] = name.strip()[:80]
            macro_library.save(self._recordings)
            self.refresh()
            self._select_id(recording["id"])

    def _delete_selected(self):
        recording = self._selected_recording()
        if not recording:
            return
        result = QtWidgets.QMessageBox.question(self, "删除录制方案", f'确定删除“{recording["name"]}”吗？')
        if result != QtWidgets.QMessageBox.Yes:
            return
        self._recordings = [item for item in self._recordings if item["id"] != recording["id"]]
        macro_library.save(self._recordings)
        self.refresh()

    def _delete_checked_or_selected(self):
        checked = self._checked_items()
        ids = [self._item_id(item) for item in checked if self._item_id(item)]
        if not ids:
            current = self._selected_recording()
            if current:
                ids = [current["id"]]
        if not ids:
            self.status_message.emit("请先勾选或选择要删除的方案")
            return
        names = [item["name"] for item in self._recordings if item["id"] in ids]
        label = names[0] if len(names) == 1 else f"{len(names)} 个方案"
        result = QtWidgets.QMessageBox.question(self, "删除录制方案", f"确定删除“{label}”吗？")
        if result != QtWidgets.QMessageBox.Yes:
            return
        self._recordings = [item for item in self._recordings if item["id"] not in ids]
        macro_library.save(self._recordings)
        self.refresh()
        self.status_message.emit(f"已删除 {len(ids)} 个方案")

    def _duplicate_selected(self):
        recording = self._selected_recording()
        if not recording:
            return
        copy_item = macro_library.create(recording["name"] + " 副本", recording["macro"])
        self._recordings.insert(0, copy_item)
        macro_library.save(self._recordings)
        self.refresh()
        self._select_id(copy_item["id"])

    def _checked_items(self):
        return [self._list.item(index) for index in range(self._list.count()) if self._list.item(index).checkState() == QtCore.Qt.Checked]

    def _item_id(self, item):
        return str(item.data(QtCore.Qt.UserRole)) if item else ""

    def _recording_by_id(self, recording_id):
        return next((item for item in self._recordings if item["id"] == recording_id), None)

    def _selected_recording(self):
        return self._recording_by_id(self._item_id(self._list.currentItem()))

    def _select_id(self, recording_id):
        for index in range(self._list.count()):
            if self._item_id(self._list.item(index)) == recording_id:
                self._list.setCurrentRow(index)
                break

    def shutdown(self):
        if self._hotkey:
            self._hotkey.stop()
        if self._recorder:
            self._recorder.stop()
            self._recorder = None

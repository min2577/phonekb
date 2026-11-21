"""PhoneKB 桌面端主窗口（PySide6 QMainWindow）。

替代之前 tkinter PairingWindow + 浏览器外跳编辑器的双入口模式，
整合为一个统一桌面 app：
  - 左侧导航（侧栏）
  - 中间页面（QStackedWidget）
  - 底部状态栏（连接状态、端口、配对码）

页面：
  - 配对页（PairingPage）：二维码 + 配对码 + IP
  - 编辑器页（EditorPage）：单层控制组件画布
"""
from __future__ import annotations

import logging
from typing import Callable, Optional

from PySide6 import QtCore, QtGui, QtWidgets

import server
from pages.pairing_page import PairingPage
from pages.editor_page import EditorPage
from pages.macro_compare_page import MacroComparePage


log = logging.getLogger("phonekb.main_window")


class MainWindow(QtWidgets.QMainWindow):
    """PhoneKB 统一桌面主窗口。"""

    closed_to_tray = QtCore.Signal()
    regenerate_requested = QtCore.Signal()

    def __init__(self, pairing_info: dict, on_regenerate: Optional[Callable[[], dict]] = None):
        super().__init__()
        self.setWindowTitle("PhoneKB  ·  手机键盘")
        self.resize(1180, 760)
        self.setMinimumSize(900, 600)

        self._on_regenerate_cb = on_regenerate
        self._info = dict(pairing_info)

        self._build_ui()
        self._build_statusbar()
        self._refresh_pairing(self._info)

        # 轮询连接状态
        self._status_timer = QtCore.QTimer(self)
        self._status_timer.timeout.connect(self._refresh_connection_status)
        self._status_timer.start(1500)

    # ---------- UI 构建 ----------

    def _build_ui(self):
        central = QtWidgets.QWidget()
        central.setStyleSheet("background: #f4f5f7;")
        layout = QtWidgets.QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 左侧导航（始终显示，不被任何页面"吃掉"）
        self._nav = QtWidgets.QListWidget()
        self._nav.setFixedWidth(180)
        self._nav.setFrameShape(QtWidgets.QFrame.NoFrame)
        self._nav.setStyleSheet("""
            QListWidget {
                background: #1f2330;
                color: #d0d4dd;
                border: none;
                padding: 8px 0;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 12px 16px;
                border-left: 3px solid transparent;
            }
            QListWidget::item:hover {
                background: #2a2f3e;
            }
            QListWidget::item:selected {
                background: #2a2f3e;
                color: #ffffff;
                border-left: 3px solid #42a5f5;
            }
        """)
        self._nav.addItem(QtWidgets.QListWidgetItem("📱  配对"))
        self._nav.addItem(QtWidgets.QListWidgetItem("🎮  手柄布局编辑器"))
        self._nav.addItem(QtWidgets.QListWidgetItem("⏱  宏录制与对比"))
        self._nav.addItem(QtWidgets.QListWidgetItem("⚙  设置（即将推出）"))
        self._nav.item(3).setFlags(QtCore.Qt.NoItemFlags)  # 占位，禁用
        self._nav.setCurrentRow(0)
        self._nav.currentRowChanged.connect(self._switch_page)
        layout.addWidget(self._nav)

        # 右侧页面栈
        self._stack = QtWidgets.QStackedWidget()
        self._stack.setStyleSheet("background: #f4f5f7;")

        # 配对页
        self._pairing_page = PairingPage(self._info)
        self._pairing_page.regenerate_requested.connect(self.regenerate_requested.emit)
        self._pairing_page.closed.connect(self.hide)
        self._stack.addWidget(self._pairing_page)

        # 编辑器页（纯 Qt 控件，不再嵌网页）
        self._editor_page = EditorPage()
        self._editor_page.status_message.connect(self._show_status_msg)
        self._editor_page.back_requested.connect(self._on_editor_back)
        self._stack.addWidget(self._editor_page)

        # 宏录制与多方案时序对比
        self._macro_page = MacroComparePage()
        self._macro_page.status_message.connect(self._show_status_msg)
        self._stack.addWidget(self._macro_page)

        layout.addWidget(self._stack, stretch=1)

        self.setCentralWidget(central)

    def _build_statusbar(self):
        sb = self.statusBar()
        sb.setStyleSheet("background: #1f2330; color: #d0d4dd; padding: 4px 12px;")
        self._sb_connection = QtWidgets.QLabel("连接：0 台")
        self._sb_ports = QtWidgets.QLabel("端口：9876 / 9877 / 9878")
        self._sb_pairing = QtWidgets.QLabel("配对码：——————")
        self._sb_ip = QtWidgets.QLabel("IP：——————")
        for w in (self._sb_connection, self._sb_ports, self._sb_pairing, self._sb_ip):
            w.setStyleSheet("color: #d0d4dd; padding: 0 12px;")
            sb.addPermanentWidget(w)
        sb.showMessage("就绪")

    # ---------- 页面切换 ----------

    def _switch_page(self, index: int):
        if 0 <= index < self._stack.count():
            self._stack.setCurrentIndex(index)
            self._apply_page_chrome(index)
            if index == 1:
                self._editor_page.refresh()
            elif index == 2:
                self._macro_page.refresh()

    def _apply_page_chrome(self, index: int):
        """让编辑器使用完整工作区，其他页面继续使用应用级导航。"""
        titles = {0: "PhoneKB · 配对", 1: "PhoneKB · 手柄布局编辑器", 2: "PhoneKB · 宏录制与对比"}
        self.setWindowTitle(titles.get(index, "PhoneKB · 手机键盘"))
        editor_active = index == 1
        self._nav.setVisible(not editor_active)
        self.statusBar().setVisible(not editor_active)

    def _on_editor_back(self):
        """编辑器页面按下「← 返回」或 Esc 时切回配对页。"""
        if self._editor_page.is_dirty():
            ret = QtWidgets.QMessageBox.question(
                self,
                "未保存的修改",
                "当前布局有未保存的修改，确定要返回配对页吗？",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if ret != QtWidgets.QMessageBox.Yes:
                return
        self._nav.setCurrentRow(0)

    def show_pairing_page(self):
        self._nav.setCurrentRow(0)
        self._apply_page_chrome(0)
        self.show()
        self.raise_()
        self.activateWindow()

    def show_editor_page(self):
        self._nav.setCurrentRow(1)
        self._apply_page_chrome(1)
        self._editor_page.refresh()
        self.showMaximized()
        self.raise_()
        self.activateWindow()

    # ---------- 数据 ----------

    def update_pairing_info(self, info: dict):
        self._info = dict(info)
        self._refresh_pairing(self._info)

    def _refresh_pairing(self, info: dict):
        self._info = dict(info)
        self._pairing_page.on_info_updated(self._info)
        code = str(self._info.get("code", ""))
        lan_ip = str(self._info.get("lan_ip", ""))
        port = self._info.get("port", 9876)
        self._sb_pairing.setText(f"配对码：{code or '——————'}")
        self._sb_ip.setText(f"IP：{lan_ip}:{port}" if lan_ip else "IP：——————")

    # ---------- 状态栏轮询 ----------

    def _refresh_connection_status(self):
        try:
            n = len(getattr(server, "_sessions", {}))
            self._sb_connection.setText(f"连接：{n} 台")
        except Exception:
            self._sb_connection.setText("连接：—")

    def _show_status_msg(self, msg: str):
        sb = self.statusBar()
        sb.showMessage(msg, 4000)

    # ---------- 关闭事件：最小化到托盘 ----------

    def closeEvent(self, event: QtGui.QCloseEvent):
        if self._editor_page.is_dirty():
            ret = QtWidgets.QMessageBox.question(
                self,
                "未保存的修改",
                "当前布局有未保存的修改，确定要最小化到托盘吗？",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if ret == QtWidgets.QMessageBox.No:
                event.ignore()
                return
        event.ignore()
        self.hide()
        self.closed_to_tray.emit()

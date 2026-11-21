"""配对页：从 pairing_display.py 移植到 PySide6 QWidget。

显示二维码 + 6 位配对码 + IP/端口 + 操作按钮。
完全替代原来的 tkinter 弹窗，作为 MainWindow 的第一个 page。
"""
from __future__ import annotations

import io

import qrcode
from PySide6 import QtCore, QtGui, QtWidgets

import pairing


class PairingPage(QtWidgets.QWidget):
    """配对页：展示给手机扫的二维码 + 配对码 + IP/端口。"""

    regenerate_requested = QtCore.Signal()
    closed = QtCore.Signal()

    def __init__(self, pairing_info: dict, parent=None):
        super().__init__(parent)
        self._info = dict(pairing_info)
        self._build_ui()
        self.refresh(self._info)

        # QR tokens expire after 60 seconds. Keep the payload scannable while
        # the pairing page remains open without changing the visible UI.
        self._qr_refresh_timer = QtCore.QTimer(self)
        self._qr_refresh_timer.timeout.connect(self._refresh_qr_token)
        self._qr_refresh_timer.start(30_000)

    # ---------- UI 构建 ----------

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(10)

        title = QtWidgets.QLabel("📱 手机键盘")
        title_font = QtGui.QFont("Microsoft YaHei UI", 18, QtGui.QFont.Bold)
        title.setFont(title_font)
        title.setAlignment(QtCore.Qt.AlignCenter)
        root.addWidget(title)

        subtitle = QtWidgets.QLabel("用微信扫码 / 手动输入配对码连接电脑")
        sub_font = QtGui.QFont("Microsoft YaHei UI", 9)
        subtitle.setFont(sub_font)
        subtitle.setStyleSheet("color: #666;")
        subtitle.setAlignment(QtCore.Qt.AlignCenter)
        root.addWidget(subtitle)

        # 二维码
        qr_frame = QtWidgets.QFrame()
        qr_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        qr_frame.setStyleSheet("background: white; border: 1px solid #ddd;")
        qr_layout = QtWidgets.QVBoxLayout(qr_frame)
        qr_layout.setContentsMargins(8, 8, 8, 8)
        self._qr_label = QtWidgets.QLabel()
        self._qr_label.setAlignment(QtCore.Qt.AlignCenter)
        self._qr_label.setMinimumSize(220, 220)
        qr_layout.addWidget(self._qr_label)
        root.addWidget(qr_frame, alignment=QtCore.Qt.AlignCenter)

        # 配对码行
        code_row = QtWidgets.QHBoxLayout()
        code_label = QtWidgets.QLabel("配对码")
        code_label.setFont(QtGui.QFont("Microsoft YaHei UI", 10))
        code_label.setStyleSheet("color: #444;")
        code_row.addWidget(code_label)

        self._code_value = QtWidgets.QLabel("——————")
        code_font = QtGui.QFont("Consolas", 22, QtGui.QFont.Bold)
        code_font.setLetterSpacing(QtGui.QFont.AbsoluteSpacing, 4)
        self._code_value.setFont(code_font)
        self._code_value.setStyleSheet("color: #0066cc; padding: 4px 12px; background: #f5f9ff; border-radius: 4px;")
        self._code_value.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        code_row.addWidget(self._code_value, stretch=1)

        copy_code_btn = QtWidgets.QPushButton("复制")
        copy_code_btn.setFixedWidth(64)
        copy_code_btn.clicked.connect(self._copy_code)
        code_row.addWidget(copy_code_btn)
        root.addLayout(code_row)

        # IP / 端口行
        addr_row = QtWidgets.QHBoxLayout()
        addr_label = QtWidgets.QLabel("地址")
        addr_label.setFont(QtGui.QFont("Microsoft YaHei UI", 10))
        addr_label.setStyleSheet("color: #444;")
        addr_row.addWidget(addr_label)

        self._addr_value = QtWidgets.QLabel("——————")
        addr_font = QtGui.QFont("Consolas", 11)
        self._addr_value.setFont(addr_font)
        self._addr_value.setStyleSheet("color: #333; padding: 4px 12px; background: #fafafa; border-radius: 4px;")
        self._addr_value.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        addr_row.addWidget(self._addr_value, stretch=1)

        copy_addr_btn = QtWidgets.QPushButton("复制")
        copy_addr_btn.setFixedWidth(64)
        copy_addr_btn.clicked.connect(self._copy_addr)
        addr_row.addWidget(copy_addr_btn)
        root.addLayout(addr_row)

        root.addStretch(1)

        # 提示
        hint = QtWidgets.QLabel(
            "操作步骤：\n"
            "  1. 手机和电脑连同一个 WiFi（或用 USB / 蓝牙）\n"
            "  2. 打开手机 HBuilderX 基座 → 微信扫码或输配对码\n"
            "  3. 连上后切到「手柄布局编辑器」自定义布局"
        )
        hint.setFont(QtGui.QFont("Microsoft YaHei UI", 9))
        hint.setStyleSheet("color: #555; background: #f5f5f5; padding: 12px; border-radius: 6px;")
        hint.setWordWrap(True)
        root.addWidget(hint)

        # 底部按钮
        btn_row = QtWidgets.QHBoxLayout()
        self._regen_btn = QtWidgets.QPushButton("🔄  重新生成配对码")
        self._regen_btn.clicked.connect(self.regenerate_requested.emit)
        btn_row.addWidget(self._regen_btn)

        btn_row.addStretch(1)

        close_btn = QtWidgets.QPushButton("最小化到托盘")
        close_btn.clicked.connect(self.closed.emit)
        btn_row.addWidget(close_btn)
        root.addLayout(btn_row)

    # ---------- 数据刷新 ----------

    def refresh(self, info: dict):
        """配对信息变更时调用，重新渲染二维码和配对码。"""
        self._info = dict(info)
        code = str(self._info.get("code", ""))
        lan_ip = str(self._info.get("lan_ip", ""))
        port = self._info.get("port", 9876)
        secret = str(self._info.get("secret", ""))

        # Android 扫码入口消费 pairing.py 的短期 HMAC token 格式。不要把
        # 长期 secret 放进二维码，否则既无法被当前客户端识别，也会泄密。
        fresh = pairing.refresh_pairing_info(secret, lan_ip, port)
        self._info.update(fresh)
        payload = fresh["ws_url"]
        self._qr_label.setPixmap(self._make_qr_pixmap(payload, size=220))

        self._code_value.setText(code or "——————")
        self._addr_value.setText(f"{lan_ip}:{port}" if lan_ip else "——————")

    def on_info_updated(self, info: dict):
        self.refresh(info)

    def _refresh_qr_token(self):
        self.refresh(self._info)

    # ---------- 工具 ----------

    @staticmethod
    def _make_qr_pixmap(text: str, size: int = 220) -> QtGui.QPixmap:
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=6,
            border=2,
        )
        qr.add_data(text)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        # PIL.Image -> QPixmap
        data = img.tobytes("raw", "RGB")
        qimg = QtGui.QImage(data, img.width, img.height, img.width * 3, QtGui.QImage.Format_RGB888)
        pixmap = QtGui.QPixmap.fromImage(qimg)
        return pixmap.scaled(size, size, QtCore.Qt.KeepAspectRatio, QtCore.Qt.FastTransformation)

    def _copy_code(self):
        code = str(self._info.get("code", ""))
        if code:
            QtWidgets.QApplication.clipboard().setText(code)
            self._toast("配对码已复制")

    def _copy_addr(self):
        lan_ip = str(self._info.get("lan_ip", ""))
        port = self._info.get("port", 9876)
        if lan_ip:
            QtWidgets.QApplication.clipboard().setText(f"{lan_ip}:{port}")
            self._toast("地址已复制")

    def _toast(self, msg: str):
        """简单提示：状态栏 2 秒后还原。"""
        top = self.window()
        if top is None:
            return
        sb = getattr(top, "statusBar", None)
        if sb is None:
            return
        bar = sb()
        prev = bar.currentMessage()
        bar.showMessage(msg, 2000)
        QtCore.QTimer.singleShot(2100, lambda: bar.showMessage(prev, 0))

"""pairing_display.py - tkinter 配对窗口：显示二维码 + 配对码 + IP。"""
import io
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

import pairing


class PairingWindow:
    """一次性弹窗：二维码 + 6 位配对码 + IP/端口 + 操作提示。"""

    def __init__(self, pairing_info: dict, on_regenerate=None, on_close=None):
        self.info = pairing_info
        self.on_regenerate = on_regenerate
        self.on_close = on_close
        self._tk_img = None  # 防止被 GC

        self.root = tk.Tk()
        self.root.title("手机键盘 — 配对")
        self.root.geometry("420x520")
        self.root.resizable(False, False)
        self._build()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build(self):
        frm = ttk.Frame(self.root, padding=16)
        frm.pack(fill=tk.BOTH, expand=True)

        # 标题
        ttk.Label(
            frm, text="📱 手机键盘",
            font=("Microsoft YaHei UI", 16, "bold"),
        ).pack(pady=(0, 2))
        ttk.Label(
            frm, text="用微信扫码 / 手动输入配对码连接电脑",
            font=("Microsoft YaHei UI", 9),
        ).pack(pady=(0, 12))

        # 二维码
        img = Image.open(io.BytesIO(self.info["qr_png"]))
        img = img.resize((240, 240), Image.NEAREST)
        self._tk_img = ImageTk.PhotoImage(img)
        self._qr_label = ttk.Label(frm, image=self._tk_img, relief=tk.SOLID, borderwidth=1)
        self._qr_label.pack(pady=4)

        # 配对码（大字号）—— 用 tk.Label 不用 ttk，避免某些主题下不渲染
        code_frame = tk.Frame(frm, bg="#f5f5f5")
        code_frame.pack(pady=(14, 4))
        tk.Label(
            code_frame, text="配对码：",
            font=("Microsoft YaHei UI", 11),
            bg="#f5f5f5", fg="#444",
        ).pack(side=tk.LEFT, padx=(0, 8))
        self._code_label = tk.Label(
            code_frame, text=self.info["code"],
            font=("Consolas", 28, "bold"),
            bg="#0066cc", fg="white",
            padx=16, pady=4,
        )
        self._code_label.pack(side=tk.LEFT, padx=(0, 8))
        # 复制按钮
        self._copy_btn = tk.Button(
            code_frame, text="📋 复制",
            font=("Microsoft YaHei UI", 10),
            bg="white", fg="#0066cc",
            activebackground="#0066cc", activeforeground="white",
            relief=tk.SOLID, bd=1,
            padx=12, pady=4,
            cursor="hand2",
            command=self._copy_code,
        )
        self._copy_btn.pack(side=tk.LEFT)

        # IP / 端口 + 复制按钮
        ip_frame = tk.Frame(frm, bg="#f5f5f5")
        ip_frame.pack(pady=(4, 8))
        self._ip_label = tk.Label(
            ip_frame, text=f"电脑 IP：{self.info['lan_ip']}    端口：{self.info['port']}",
            font=("Consolas", 10), fg="#444", bg="#f5f5f5",
        )
        self._ip_label.pack(side=tk.LEFT)
        self._copy_addr_btn = tk.Button(
            ip_frame, text="📋 复制",
            font=("Microsoft YaHei UI", 10),
            bg="white", fg="#0066cc",
            activebackground="#0066cc", activeforeground="white",
            relief=tk.SOLID, bd=1,
            padx=12, pady=4,
            cursor="hand2",
            command=self._copy_address,
        )
        self._copy_addr_btn.pack(side=tk.LEFT, padx=(16, 0))

        # 提示
        tip = "• 扫码即连（推荐）\n• 不想扫码？打开小程序手动输入 IP + 6 位配对码"
        ttk.Label(
            frm, text=tip,
            font=("Microsoft YaHei UI", 9),
            foreground="#666", justify=tk.LEFT,
        ).pack(pady=6)

        # 关闭按钮
        ttk.Button(frm, text="知道了（最小化到托盘）", command=self._on_close).pack(pady=(8, 0))
        regen_btn = ttk.Button(frm, text="🔄 重新生成配对码", command=self._on_regenerate_clicked)
        regen_btn.pack(pady=(4, 0))

        self.root.bind("<Map>", lambda e: self._refresh_qr())
        self.root.after(30000, self._auto_refresh_loop)

    def _copy_code(self):
        """复制配对码到剪贴板，按钮短暂反馈。"""
        code = self.info["code"]
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(code)
            self.root.update()  # tkinter 必须 update 才会真正写入剪贴板
            self._copy_btn.config(text="✓ 已复制", bg="#4caf50", fg="white")
        except Exception as e:
            self._copy_btn.config(text="✗ 失败")
            print("copy failed:", e)
        # 1.5 秒后恢复
        self.root.after(1500, self._reset_copy_btn)

    def _reset_copy_btn(self):
        try:
            self._copy_btn.config(text="📋 复制", bg="white", fg="#0066cc")
        except Exception:
            pass

    def _copy_address(self):
        """复制 IP:PORT 到剪贴板。"""
        addr = f"{self.info['lan_ip']}:{self.info['port']}"
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(addr)
            self.root.update()
            self._copy_addr_btn.config(text="✓ 已复制", bg="#4caf50", fg="white")
        except Exception as e:
            self._copy_addr_btn.config(text="✗ 失败")
            print("copy addr failed:", e)
        self.root.after(1500, self._reset_addr_btn)

    def _reset_addr_btn(self):
        try:
            self._copy_addr_btn.config(text="📋 复制", bg="white", fg="#0066cc")
        except Exception:
            pass

    def _on_close(self):
        if self.on_close:
            try:
                self.on_close()
            except Exception:
                pass
        try:
            self.root.destroy()
        except Exception:
            pass


    def _on_regenerate_clicked(self):
        if not self.on_regenerate:
            return
        try:
            new_info = self.on_regenerate()
            if new_info:
                self.info = new_info
                if hasattr(self, "_code_label"):
                    self._code_label.configure(text=self.info["code"])
                self._refresh_qr()
        except Exception as e:
            print("[pairing_display] regenerate failed: %s" % e, flush=True)

    def on_info_updated(self, new_info: dict):
        """被 App.regenerate_pairing 调用:刷新窗口的 code/QR/IP 显示。"""
        self.info = new_info
        if hasattr(self, "_code_label"):
            self._code_label.configure(text=self.info["code"])
        self._refresh_qr()
    def show(self):
        self.root.mainloop()
    def _refresh_qr(self):
        """重新生成 QR(token 60s 过期,需周期刷新);顺手清掉 server 失败计数。"""
        try:
            import pairing
            fresh = pairing.refresh_pairing_info(
                self.info["secret"], self.info["lan_ip"], self.info["port"])
            self.info["ws_url"] = fresh["ws_url"]
            self.info["qr_png"] = fresh["qr_png"]
            img = Image.open(io.BytesIO(fresh["qr_png"]))
            img = img.resize((240, 240), Image.NEAREST)
            self._tk_img = ImageTk.PhotoImage(img)
            self._qr_label.configure(image=self._tk_img)
            self._ip_label.configure(text=f"电脑 IP:{fresh['lan_ip']}    端口:{fresh['port']}")
            try:
                import server, time
                now = time.time()
                for ip in list(server._PAIR_ATTEMPTS.keys()):
                    rec = server._PAIR_ATTEMPTS[ip]
                    if rec.get("lockout_until", 0) < now and rec.get("count", 0) == 0:
                        del server._PAIR_ATTEMPTS[ip]
            except Exception:
                pass
        except Exception as e:
            print(f"[pairing_display] refresh qr failed: {e}", flush=True)

    def _auto_refresh_loop(self):
        """每 30 秒刷一次 QR,避免 60s token 窗口过期。"""
        try:
            self._refresh_qr()
        finally:
            try:
                self.root.after(30000, self._auto_refresh_loop)
            except Exception:
                pass


if __name__ == "__main__":
    import pairing
    info = pairing.create_pairing()
    PairingWindow(info).show()

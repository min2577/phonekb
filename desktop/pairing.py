"""pairing.py - 一次启动生成一组配对信息：secret、配对码、LAN IP、二维码 PNG。

持久化：第一次启动后保存到 pairing.json，下次启动读同一个。
要换配对码：删 pairing.json 重启。
"""
import hashlib
import hmac
import io
import json
import os
import secrets
import socket
import string
import time

import qrcode

_PAIRING_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pairing.json")


def _generate_code() -> str:
    """生成 6 位易读配对码。去除 0/O/1/I/L 容易混淆的字符。"""
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(6))


def _get_lan_ip() -> str:
    """获取本机 LAN IP（不真实发包到 8.8.8.8，仅借用路由表）。"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def create_pairing(port: int = 9876) -> dict:
    """创建（或读取持久化的）配对信息。

    Returns:
        dict: {
            "secret": str,    # 32 字符 base64url，扫码 URL 里带
            "code": str,      # 6 位配对码（大写），手输模式用
            "lan_ip": str,
            "port": int,
            "ws_url": str,    # 扫码内容：ws://IP:port/?t=<token>（不含 secret）
            "qr_png": bytes,  # PNG 格式二维码
        }
    """
    # 优先读持久化文件（同一台电脑同一组配对，避免每次重启换码）
    if os.path.exists(_PAIRING_FILE):
        try:
            with open(_PAIRING_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            if saved.get("secret") and saved.get("code"):
                lan_ip = _get_lan_ip()
                ws_url = _make_pairing_url(lan_ip, port, saved["secret"])
                qr_png = _make_qr_png(ws_url)
                return {
                    "secret": saved["secret"],
                    "code": saved["code"],
                    "lan_ip": lan_ip,
                    "port": port,
                    "ws_url": ws_url,
                    "qr_png": qr_png,
                }
        except Exception:
            pass  # 文件坏了，重新生成

    # 关键修复：secret 必须只用字母数字，这样 secret[:6].upper() 才是 [A-Z0-9]{6}
    # 让 secret 和 code 强绑定：code = secret 前 6 位大写
    alphabet = string.ascii_letters + string.digits
    secret = ''.join(secrets.choice(alphabet) for _ in range(32))
    code = secret[:6].upper()
    lan_ip = _get_lan_ip()
    ws_url = _make_pairing_url(lan_ip, port, secret)
    qr_png = _make_qr_png(ws_url)

    # 保存到文件，下次启动读
    try:
        with open(_PAIRING_FILE, "w", encoding="utf-8") as f:
            json.dump({"secret": secret, "code": code}, f)
        # 限制文件权限：仅当前用户可读写
        try:
            os.chmod(_PAIRING_FILE, 0o600)
        except (OSError, AttributeError):
            pass  # Windows 上 os.chmod 部分支持
    except Exception:
        pass

    return {
        "secret": secret,
        "code": code,
        "lan_ip": lan_ip,
        "port": port,
        "ws_url": ws_url,
        "qr_png": qr_png,
    }


def _make_pairing_token(secret: str, ts: int = None) -> str:
    """生成 QR 码 / URL 用的短期 token：HMAC(secret, ts).hex[:16]

    ts 在 server 端校验是否在 60s 窗口内。secret 本身不出现在 token 中。"""
    if ts is None:
        ts = int(time.time())
    mac = hmac.new(secret.encode("ascii"), str(ts).encode("ascii"), hashlib.sha256).hexdigest()[:16]
    return f"{ts}.{mac}"


def _make_pairing_url(lan_ip: str, port: int, secret: str) -> str:
    """生成不带 secret 的 URL（QR 码用）。包含 token 和 code（code 仅 UI 展示）。"""
    token = _make_pairing_token(secret)
    code = secret[:6].upper()
    return f"ws://{lan_ip}:{port}/?t={token}&code={code}"



def refresh_pairing_info(secret: str, lan_ip: str, port: int) -> dict:
    """基于现有 secret 生成新 token + QR(code/secret 不变)。"""
    token = _make_pairing_token(secret)
    code = secret[:6].upper()
    ws_url = f"ws://{lan_ip}:{port}/?t={token}&code={code}"
    qr_png = _make_qr_png(ws_url)
    return {
        "secret": secret,
        "code": code,
        "lan_ip": lan_ip,
        "port": port,
        "ws_url": ws_url,
        "qr_png": qr_png,
    }
def _make_qr_png(ws_url: str) -> bytes:
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(ws_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


if __name__ == "__main__":
    info = create_pairing()
    print(f"Secret:  {info['secret']}")
    print(f"Code:    {info['code']}")
    print(f"LAN IP:  {info['lan_ip']}")
    print(f"Port:    {info['port']}")
    print(f"WS URL:  {info['ws_url']}")
    print(f"QR PNG:  {len(info['qr_png'])} bytes")

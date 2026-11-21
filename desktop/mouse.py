"""mouse.py - 通过 SendInput 的 MOUSEINPUT 控制 Windows 鼠标。

第一性原理：SendInput(INPUT_MOUSE) 把合成鼠标事件注入到 Windows 输入队列。
和真鼠标等价，能控制光标移动、点击、滚轮、拖动。

坐标系：
  - 默认：相对移动（dx/dy 是相对偏移像素）
  - 绝对：MOUSEEVENTF_ABSOLUTE + MOUSEEVENTF_MOVE，dx/dy 是 0..65535 归一化坐标
    绝对坐标转换：dx = x * 65535 / screen_width
"""
import ctypes
import keytrigger
import time
from ctypes import wintypes

import keytrigger  # 复用 INPUT / MOUSEINPUT 结构

user32 = ctypes.WinDLL("user32", use_last_error=True)

# === MOUSEEVENTF 常量（Windows 头文件 winuser.h）===
MOUSEEVENTF_MOVE       = 0x0001
MOUSEEVENTF_LEFTDOWN   = 0x0002
MOUSEEVENTF_LEFTUP     = 0x0004
MOUSEEVENTF_RIGHTDOWN  = 0x0008
MOUSEEVENTF_RIGHTUP    = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP   = 0x0040
MOUSEEVENTF_WHEEL      = 0x0800
MOUSEEVENTF_HWHEEL     = 0x01000
MOUSEEVENTF_ABSOLUTE   = 0x8000
WHEEL_DELTA            = 120  # 一个 notch

INPUT_MOUSE = 0


def _send(dx=0, dy=0, flags=MOUSEEVENTF_MOVE, mouseData=0):
    """底层：发一次 MOUSEINPUT。返回 SendInput 注入成功的事件数（0=失败）。"""
    inp = keytrigger.INPUT()
    inp.type = INPUT_MOUSE
    inp.mi.dx = dx
    inp.mi.dy = dy
    inp.mi.mouseData = mouseData
    inp.mi.dwFlags = flags
    inp.mi.time = 0
    inp.mi.dwExtraInfo = None
    n = user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
    return n


def move(dx: int, dy: int) -> int:
    """相对移动光标 dx, dy 像素。"""
    return _send(dx=dx, dy=dy, flags=MOUSEEVENTF_MOVE)


def move_abs(x: int, y: int) -> int:
    """绝对移动光标到屏幕坐标 (x, y) 像素。"""
    sw = user32.GetSystemMetrics(0)  # SM_CXSCREEN
    sh = user32.GetSystemMetrics(1)  # SM_CYSCREEN
    if sw <= 0 or sh <= 0:
        return 0
    # 0..65535 归一化（注意 65535 而不是 65536，对应最右下角）
    nx = int(x * 65535 / (sw - 1))
    ny = int(y * 65535 / (sh - 1))
    return _send(dx=nx, dy=ny, flags=MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE)


def click(button="left", count=1):
    """单击按钮 button (left/right/middle)，count 次（双击传 2）。"""
    down_flag, up_flag = {
        "left":   (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP),
        "right":  (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP),
        "middle": (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP),
    }[button]
    n = 0
    for _ in range(count):
        n += _send(flags=down_flag)
        time.sleep(0.01)
        n += _send(flags=up_flag)
        if count > 1:
            time.sleep(0.05)
    return n


def down(button="left"):
    """按下鼠标按钮不释放（用于拖动）。"""
    flag = {"left": MOUSEEVENTF_LEFTDOWN, "right": MOUSEEVENTF_RIGHTDOWN, "middle": MOUSEEVENTF_MIDDLEDOWN}[button]
    return _send(flags=flag)


def up(button="left"):
    """释放鼠标按钮。"""
    flag = {"left": MOUSEEVENTF_LEFTUP, "right": MOUSEEVENTF_RIGHTUP, "middle": MOUSEEVENTF_MIDDLEUP}[button]
    return _send(flags=flag)


def wheel(delta: int) -> int:
    """滚轮：delta 正数向上滚一格，负数向下（每格 120）。"""
    return _send(mouseData=delta, flags=MOUSEEVENTF_WHEEL)


def hwheel(delta: int) -> int:
    """水平滚轮。"""
    return _send(mouseData=delta, flags=MOUSEEVENTF_HWHEEL)


def zoom(delta: int) -> int:
    """通用应用缩放：按住 Ctrl 时发送垂直滚轮。"""
    keytrigger.key_down("ctrl")
    try:
        return wheel(delta)
    finally:
        keytrigger.key_up("ctrl")


def position():
    """获取当前光标位置。"""
    pt = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return (pt.x, pt.y)


# === 自测：画个圆圈 ===
if __name__ == "__main__":
    import math
    x0, y0 = position()
    print(f"start: ({x0}, {y0})", flush=True)
    n = 100
    r = 100
    ok = 0
    for i in range(n):
        angle = 2 * math.pi * i / n
        dx = int(r * math.cos(angle)) - int(r * math.cos(2 * math.pi * (i - 1) / n))
        dy = int(r * math.sin(angle)) - int(r * math.sin(2 * math.pi * (i - 1) / n))
        m = move(dx, dy)
        ok += m
        time.sleep(0.01)
    x1, y1 = position()
    print(f"end: ({x1}, {y1}), injected {ok}/{n}", flush=True)

"""Editor timeline controls shared by WiFi, USB and Bluetooth transports."""

import keytrigger


MAX_STEPS_PER_MESSAGE = 12


def _steps(delta):
    value = int(delta or 0)
    return max(-MAX_STEPS_PER_MESSAGE, min(MAX_STEPS_PER_MESSAGE, value))


def execute(op, delta, hwnd=0):
    steps = _steps(delta)
    if not steps:
        return True, ""
    if not hwnd:
        return False, "请先绑定剪映窗口"
    if not keytrigger.focus_window(hwnd):
        return False, "绑定的窗口已不可用，请重新绑定"

    key = "right" if steps > 0 else "left"
    modifiers = []
    if op == "zoom":
        key = "=" if steps > 0 else "-"
        modifiers = ["ctrl"]
    elif op != "scrub":
        return False, "不支持的时间轴操作"

    for _ in range(abs(steps)):
        if not keytrigger.simulate_key(modifiers, key):
            return False, "时间轴操作执行失败"
    return True, ""

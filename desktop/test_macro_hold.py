import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server


def check(condition, label):
    if not condition:
        raise AssertionError(label)
    print("PASS " + label)


def run():
    events = []
    original = (
        server.keytrigger.key_down,
        server.keytrigger.key_up,
        server.keytrigger.simulate_key,
        server.mouse.down,
        server.mouse.up,
        server.mouse.click,
        server.mouse.wheel,
        server.asyncio.sleep,
    )
    try:
        server.keytrigger.key_down = lambda key: events.append(("key_down", key)) or True
        server.keytrigger.key_up = lambda key: events.append(("key_up", key)) or True
        server.keytrigger.simulate_key = lambda mods, key: events.append(("key_tap", tuple(mods), key)) or True
        server.mouse.down = lambda button: events.append(("mouse_down", button)) or True
        server.mouse.up = lambda button: events.append(("mouse_up", button)) or True
        server.mouse.click = lambda button, count: events.append(("mouse_click", button, count)) or True
        server.mouse.wheel = lambda delta: events.append(("wheel", delta)) or True

        async def fake_sleep(seconds):
            events.append(("sleep", round(seconds, 3)))

        server.asyncio.sleep = fake_sleep

        ws = object()
        asyncio.run(server._execute_macro(ws, [
            {"type": "key", "key": "w", "mode": "down"},
            {"type": "mouse", "op": "click", "button": "left"},
            {"type": "key", "key": "w", "mode": "up"},
        ], interval_ms=0))
        check(events == [("key_down", "w"), ("mouse_click", "left", 1), ("key_up", "w")], "W remains down through mouse click")

        events.clear()
        asyncio.run(server._execute_macro(ws, [
            {"type": "key", "key": "a", "mode": "tap"},
            {"type": "mouse", "op": "click", "button": "left"},
        ], interval_ms=50))
        check(events == [("key_tap", (), "a"), ("sleep", 0.05), ("mouse_click", "left", 1)], "uniform interval runs between adjacent actions")

        events.clear()
        asyncio.run(server._execute_macro(ws, [
            {"type": "key", "key": "a", "mode": "tap"},
            {"type": "wait_ms", "value": 200},
            {"type": "mouse", "op": "click", "button": "left"},
        ], interval_ms=50))
        check(events == [("key_tap", (), "a"), ("sleep", 0.2), ("mouse_click", "left", 1)], "explicit wait replaces the uniform interval")

        events.clear()
        asyncio.run(server._execute_macro(ws, [{"type": "key", "key": "w", "mode": "down"}], interval_ms=0))
        check(events == [("key_down", "w"), ("key_up", "w")], "unmatched key down is released")
        check(ws not in server._gamepad_held_keys, "macro leaves no held keyboard state")
    finally:
        (
            server.keytrigger.key_down,
            server.keytrigger.key_up,
            server.keytrigger.simulate_key,
            server.mouse.down,
            server.mouse.up,
            server.mouse.click,
            server.mouse.wheel,
            server.asyncio.sleep,
        ) = original


if __name__ == "__main__":
    run()

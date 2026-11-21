"""Export PhoneKB macros into the local Acer MouseHub macro database."""
from __future__ import annotations

import datetime
import glob
import os
import shutil
import sqlite3
import subprocess

from keymap import MOD_NAME_MAP, resolve_key


DB_GLOB = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Acer MouseHub Files", "db", "*.db")
MOUSE_VALUES = {"left": 1, "right": 2, "middle": 4}


def is_running():
    try:
        output = subprocess.check_output(["tasklist", "/FI", "IMAGENAME eq Acer MouseHub.exe", "/NH"], text=True, errors="ignore")
        return "Acer MouseHub.exe".lower() in output.lower()
    except (OSError, subprocess.SubprocessError):
        return False


def find_active_database():
    candidates = []
    for path in glob.glob(DB_GLOB):
        try:
            con = sqlite3.connect("file:" + path + "?mode=ro", uri=True)
            tables = {row[0] for row in con.execute("select name from sqlite_master where type='table'")}
            macro_count = con.execute("select count(*) from t_macro_data").fetchone()[0] if "t_macro_data" in tables else 0
            con.close()
            if {"t_macro_data", "t_macrorecord"}.issubset(tables):
                candidates.append((macro_count > 0, os.path.getmtime(path), path))
        except (OSError, sqlite3.Error):
            continue
    return max(candidates, default=(False, 0, ""))[2]


def convert_steps(macro, tap_ms=10):
    """Convert PhoneKB steps to MouseHub (type, description, value) rows."""
    rows = []

    def wait(value):
        value = max(0, min(60000, int(value or 0)))
        rows.append((1, f"{value} ms", value))

    def key_event(key, is_down):
        vk = MOD_NAME_MAP.get(str(key).lower()) or resolve_key(key)
        if not vk:
            raise ValueError("MouseHub 不支持按键：" + str(key))
        rows.append((2 if is_down else 3, ("↓  " if is_down else "↑  ") + _key_label(key), int(vk)))

    def key_tap(key, duration):
        key_event(key, True)
        wait(duration)
        key_event(key, False)

    def mouse_event(button, is_down):
        value = MOUSE_VALUES.get(str(button).lower())
        if not value:
            raise ValueError("MouseHub 不支持鼠标按键：" + str(button))
        label = {1: "LB", 2: "RB", 4: "MB"}[value]
        rows.append((4 if is_down else 5, ("↓  " if is_down else "↑  ") + label, value))

    for step in (macro or {}).get("steps", []):
        if not isinstance(step, dict):
            continue
        step_type = step.get("type")
        if step_type == "wait_ms":
            wait(step.get("value", 0))
        elif step_type == "key":
            modifiers = list(step.get("modifiers") or [])
            key = step.get("key")
            mode = step.get("mode", "tap")
            keys = modifiers + ([key] if key else [])
            if mode == "down":
                for value in keys:
                    key_event(value, True)
            elif mode == "up":
                for value in reversed(keys):
                    key_event(value, False)
            else:
                for value in modifiers:
                    key_event(value, True)
                if key:
                    key_tap(key, step.get("duration_ms", tap_ms))
                for value in reversed(modifiers):
                    key_event(value, False)
        elif step_type == "mouse":
            op = step.get("op", "click")
            if op == "wheel":
                # MouseHub does not expose wheel macro events. Map wheel to 1/2.
                key_tap("1" if int(step.get("delta", 120) or 120) > 0 else "2", tap_ms)
            elif op == "down":
                mouse_event(step.get("button", "left"), True)
            elif op == "up":
                mouse_event(step.get("button", "left"), False)
            else:
                button = step.get("button", "left")
                mouse_event(button, True)
                wait(step.get("duration_ms", tap_ms))
                mouse_event(button, False)
        elif step_type == "enter":
            key_tap("enter", tap_ms)
        elif step_type == "text":
            raise ValueError("MouseHub 宏不支持文本输入步骤")
    return rows


def export_macro(name, macro, database_path=None, bind_key_code=None, bind_profile=1):
    database_path = database_path or find_active_database()
    if not database_path:
        raise RuntimeError("没有找到 Acer MouseHub 宏数据库")
    rows = convert_steps(macro)
    if not rows:
        raise ValueError("宏中没有可导出的动作")
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = database_path + ".phonekb-backup-" + timestamp
    shutil.copy2(database_path, backup_path)
    con = sqlite3.connect(database_path, timeout=2)
    try:
        con.execute("begin immediate")
        final_name = _unique_name(con, "PhoneKB-" + str(name or "宏")[:48])
        cursor = con.execute(
            "insert into t_macro_data(name,play_type,play_times,delay_type,delay_time) values(?,?,?,?,?)",
            (final_name, 0, 1, 1, 0),
        )
        macro_id = int(cursor.lastrowid)
        base = int(con.execute("select coalesce(max(delay_time),0) from t_macrorecord").fetchone()[0]) + 1
        for index, (event_type, desc, value) in enumerate(rows):
            con.execute(
                "insert into t_macrorecord(macro_id,type,record_index,desc,value,delay_time) values(?,?,?,?,?,?)",
                (macro_id, event_type, index, desc, value, base + index),
            )
        if bind_key_code is not None:
            existing = con.execute(
                "select key_id from t_key_macro_data where profile=? and fn_layer=0 and key_code=? order by key_id limit 1",
                (int(bind_profile), int(bind_key_code)),
            ).fetchone()
            values = (4, macro_id, 0, 0, final_name)
            if existing:
                con.execute(
                    "update t_key_macro_data set macro_type=?,macro_value=?,macro_value2=?,macro_value3=?,macro_desc=? where key_id=?",
                    values + (int(existing[0]),),
                )
            else:
                con.execute(
                    "insert into t_key_macro_data(profile,fn_layer,key_code,layout_value,layout_desc,macro_type,macro_value,macro_value2,macro_value3,macro_desc) values(?,?,?,?,?,?,?,?,?,?)",
                    (int(bind_profile), 0, int(bind_key_code), 0, "") + values,
                )
        con.commit()
        return {"name": final_name, "macro_id": macro_id, "events": len(rows), "backup": backup_path, "database": database_path, "bound_key_code": bind_key_code}
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def _unique_name(con, base):
    names = {row[0] for row in con.execute("select name from t_macro_data")}
    if base not in names:
        return base
    index = 2
    while f"{base}-{index}" in names:
        index += 1
    return f"{base}-{index}"


def _key_label(key):
    value = str(key or "").lower()
    labels = {"lshift": "LShift", "rshift": "RShift", "lctrl": "LCtrl", "rctrl": "RCtrl", "lalt": "LAlt", "ralt": "RAlt", "enter": "Enter"}
    return labels.get(value, value.upper())

"""layouts_loader.py - layouts.json 加载与 CRUD（V2 数据模型）。

数据结构 (V2):
{
  "version": 2,
  "active_layout_id": "vscode",
  "active_page_id": "edit",
  "grid_cols": 4,
  "layouts": [
    {
      "id": "vscode",
      "name": "VS Code",
      "icon": "💻",
      "match": { "process": ["Code.exe"], "title_contains": [] },
      "pages": [
        {
          "id": "edit",
          "name": "编辑",
          "icon": "✂",
          "slots": [
            { "r": 0, "c": 0, "span": 1, "key": { ... } }
          ]
        }
      ]
    }
  ],
  "global_pages": [
    { "id": "system", "name": "系统", "icon": "🖥", "slots": [ ... ] }
  ]
}

兼容:
  - 旧 custom_keys.json (v1) 会在首次启动时自动转换为 layouts.json。
  - 旧 v1 协议的 add/update/delete_custom_key 仍走兼容接口，返回 v2 字段。

Key 类型：
  - shortcut : { type:"shortcut", modifiers:[...], key:"f" }
  - text     : { type:"text", value:"..." }
  - mouse    : { type:"mouse", op:"click", button:"left", count:1 }
  - macro    : { type:"macro", steps:[ {type:"key", modifiers:[...], key:"..."}, ... ] }
  - link     : { type:"link", url:"..." }
  - app      : { type:"app", path:"..." }
  - codex    : { type:"codex", action:"focus_task|approve|reject", slot:1..6 }
"""
import json
import os
import secrets
import string
import threading
import sys
import time

# _MOD_MAP / _KEY_MAP 委托给 keymap.py 单一来源（keytrigger.py 也用这个）
from keymap import MOD_NAME_MAP as _MOD_MAP, VK_NAME_MAP as _KEY_MAP


# ============ Runtime paths ============
# Frozen (PyInstaller --onefile): user data lives next to PhoneKB.exe (dist/).
# Source / dev mode (__file__): data lives next to this .py.
# Why: onefile extracts to a temp MEIPASS, so __file__ points there and
#      reading user-mutable data from MEIPASS is wrong.

_DIR = os.path.dirname(os.path.abspath(__file__))
LAYOUTS_FILE = os.path.join(_DIR, "layouts.json")
LEGACY_FILE = os.path.join(_DIR, "custom_keys.json")
PRESETS_DIR = os.path.join(_DIR, "presets")
BACKUP_FILE = os.path.join(_DIR, "layouts.json.bak")


def _is_frozen():
    """True if running under PyInstaller frozen."""
    return getattr(sys, "frozen", False)


def _exe_dir():
    """EXE directory in frozen mode, else None."""
    if _is_frozen():
        return os.path.dirname(os.path.abspath(sys.executable))
    return None


def _write_root():
    """Primary directory for read/write runtime data files.
    Frozen: EXE dir (persistent). Dev: source dir.
    """
    exe = _exe_dir()
    return exe if exe else _DIR


def _read_roots():
    """Ordered candidate dirs for read-only search.
    Frozen: [EXE dir, _DIR (MEIPASS/source)]. Dev: [_DIR].
    """
    exe = _exe_dir()
    if exe:
        return [exe, _DIR]
    return [_DIR]


def _first_existing(name, *, is_dir=False):
    """Return first existing path among _read_roots(), or None."""
    checker = os.path.isdir if is_dir else os.path.isfile
    for root in _read_roots():
        p = os.path.join(root, name)
        if checker(p):
            return p
    return None


def _layouts_path(*, write=False):
    """Resolve layouts.json absolute path.
    write=True -> ensure parent dir exists; return primary write path.
    """
    if write:
        root = _write_root()
        path = os.path.join(root, "layouts.json")
        os.makedirs(root, exist_ok=True)
        return path
    found = _first_existing("layouts.json")
    if found:
        return found
    return os.path.join(_write_root(), "layouts.json")


def _legacy_path(*, write=False):
    if write:
        return os.path.join(_write_root(), "custom_keys.json")
    found = _first_existing("custom_keys.json")
    if found:
        return found
    return os.path.join(_write_root(), "custom_keys.json")


def _presets_dir_path():
    """First existing presets/ dir, fallback to source dir for inspection."""
    found = _first_existing("presets", is_dir=True)
    if found:
        return found
    return os.path.join(_DIR, "presets")


def _backup_path():
    """layouts.json.bak lives next to primary write target."""
    return _layouts_path(write=True) + ".bak"


# ============ Concurrency ============
# Read-modify-write ops share this lock; intra + cross-process (msvcrt.locking).
_WRITE_LOCK = threading.Lock()
_FD_LOCK_PATH = os.path.join(_DIR, ".layouts.lock")


def _file_lock_acquire(timeout: float = 5.0) -> int:
    """跨进程文件锁（Windows: msvcrt.locking）。返回 fd；失败抛 OSError。"""
    import msvcrt
    fd = os.open(_FD_LOCK_PATH, os.O_CREAT | os.O_RDWR, 0o600)
    deadline = time.time() + timeout
    while True:
        try:
            msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
            return fd
        except OSError:
            if time.time() > deadline:
                os.close(fd)
                raise
            time.sleep(0.05)


def _file_lock_release(fd: int):
    try:
        import msvcrt
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    except Exception:
        pass
    try:
        os.close(fd)
    except Exception:
        pass


# ===== 工具函数 =====

def _gen_id(label: str = "key") -> str:
    base = label.lower().strip() or "key"
    base = "".join(ch if ch.isalnum() else "_" for ch in base).strip("_") or "key"
    return base + "_" + secrets.token_hex(2)


def _vk_mods(mod_list):
    """把 ['ctrl','shift'] 翻译成 [0xA2, 0xA0]"""
    from keymap import resolve_mods
    return resolve_mods(mod_list)


def _vk_key(key: str):
    from keymap import resolve_key
    return resolve_key(key)


def _now_id() -> str:
    return secrets.token_hex(4)


# ===== 默认数据 =====

def _default_data() -> dict:
    """全新安装时的兜底 layout。"""
    return {
        "version": 2,
        "active_layout_id": "default",
        "active_page_id": "system",
        "grid_cols": 4,
        "grid_rows": 4,
        "layouts": [
            {
                "id": "default",
                "name": "默认",
                "icon": "🎯",
                "match": {"process": [], "title_contains": []},
                "pages": [
                    {
                        "id": "system",
                        "name": "系统",
                        "icon": "🖥",
                        "slots": [
                            {"r": 0, "c": 0, "span": 1, "key": _shortcut_key("copy", "复制", "Ctrl+C", ["ctrl"], "c")},
                            {"r": 0, "c": 1, "span": 1, "key": _shortcut_key("paste", "粘贴", "Ctrl+V", ["ctrl"], "v")},
                            {"r": 0, "c": 2, "span": 1, "key": _shortcut_key("cut", "剪切", "Ctrl+X", ["ctrl"], "x")},
                            {"r": 0, "c": 3, "span": 1, "key": _shortcut_key("undo", "撤销", "Ctrl+Z", ["ctrl"], "z")},
                        ],
                    }
                ],
            }
        ],
        "global_pages": [
            {
                "id": "common",
                "name": "通用",
                "icon": "⌨",
                "slots": [
                    {"r": 0, "c": 0, "span": 1, "key": _shortcut_key("enter", "Enter", "", [], "enter")},
                    {"r": 0, "c": 1, "span": 1, "key": _shortcut_key("tab", "Tab", "", [], "tab")},
                    {"r": 0, "c": 2, "span": 1, "key": _shortcut_key("backspace", "退格", "", [], "backspace")},
                    {"r": 0, "c": 3, "span": 1, "key": _shortcut_key("escape", "Esc", "", [], "escape")},
                ],
            }
        ],
    }


def _shortcut_key(key_id, label, sub, modifiers, key):
    return {
        "id": key_id,
        "label": label,
        "sub": sub,
        "icon": "",
        "type": "shortcut",
        "feedback": {"vibrate": True, "sound": False, "toast": True},
        "confirm_on_long_press": False,
        "shortcut": {"modifiers": modifiers, "key": key},
    }


# ===== 加载 / 保存 =====

def load() -> dict:
    """加载 layouts.json；不存在则尝试迁移旧 custom_keys.json；都不存在用默认。"""
    layouts_path = _first_existing("layouts.json")
    if layouts_path:
        try:
            with open(layouts_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "layouts" in data:
                repaired = _repair_misplaced_layouts(data)
                normalized = _normalize(data)
                if repaired:
                    save(normalized)
                return normalized
        except Exception as e:
            print("[layouts] load failed:", e, flush=True)

    # Migrate legacy v1
    legacy_path = _first_existing("custom_keys.json")
    if legacy_path:
        try:
            migrated = _migrate_from_v1(legacy_path)
            if migrated:
                _load_builtins(migrated)
                save(migrated)
                # Rename legacy file (do not delete, avoid data loss). Next launch skips it.
                try:
                    os.replace(legacy_path, legacy_path + ".migrated")
                except OSError:
                    pass
                return _normalize(migrated)
        except Exception as e:
            print("[layouts] migrate v1 failed:", e, flush=True)

    # 默认 + 加载内置预设
    data = _default_data()
    _load_builtins(data)
    save(data)
    return _normalize(data)


def _load_builtins(data: dict):
    """把 presets/*.json 里标 built_in=true 的 layout 合并进默认数据（不覆盖用户已有）。"""
    presets_root = _presets_dir_path()
    if not os.path.isdir(presets_root):
        return
    existing_ids = {l["id"] for l in data["layouts"]}
    for fn in sorted(os.listdir(presets_root)):
        if not fn.endswith(".json"):
            continue
        path = os.path.join(presets_root, fn)
        try:
            with open(path, "r", encoding="utf-8") as f:
                preset = json.load(f)
            if not preset.get("built_in"):
                continue
            layout_id = preset.get("id") or os.path.splitext(fn)[0]
            if layout_id in existing_ids:
                continue
            preset["id"] = layout_id
            data["layouts"].append(preset)
            existing_ids.add(layout_id)
        except Exception as e:
            print(f"[layouts] preset load failed {fn}:", e, flush=True)


def _migrate_from_v1(path: str) -> dict:
    """把旧 custom_keys.json 转成 layouts.json 格式。"""
    with open(path, "r", encoding="utf-8") as f:
        old = json.load(f)
    keys = old.get("keys", [])
    slots = []
    cols = 4
    for i, k in enumerate(keys):
        r, c = divmod(i, cols)
        slots.append({
            "r": r,
            "c": c,
            "span": 1,
            "key": _shortcut_key(
                key_id=k.get("id") or _gen_id(k.get("label", "key")),
                label=k.get("label", "?"),
                sub=k.get("sub", ""),
                modifiers=k.get("modifiers", []),
                key=k.get("key", ""),
            ),
        })
    return {
        "version": 2,
        "active_layout_id": "default",
        "active_page_id": "custom",
        "grid_cols": cols,
        "layouts": [
            {
                "id": "default",
                "name": "默认",
                "icon": "🎯",
                "match": {"process": [], "title_contains": []},
                "pages": [
                    {
                        "id": "custom",
                        "name": "自定义",
                        "icon": "⚡",
                        "slots": slots,
                    }
                ],
            }
        ],
        "global_pages": [],
    }


def _normalize(data: dict) -> dict:
    """确保所有字段都在，缺啥补啥。"""
    data.setdefault("version", 2)
    data.setdefault("active_layout_id", "default")
    data.setdefault("active_page_id", None)
    data.setdefault("grid_cols", 4)
    data.setdefault("grid_rows", 4)
    # 注：每个 slot 的 rowspan/colspan 由 _normalize_slot 设默认
    data.setdefault("layouts", [])
    data.setdefault("global_pages", [])
    data.setdefault("archived_layouts", [])
    for lay in data["layouts"] + data["archived_layouts"]:
        lay.setdefault("id", _gen_id(lay.get("name", "layout")))
        lay.setdefault("name", lay["id"])
        lay.setdefault("icon", "🎯")
        lay.setdefault("match", {"process": [], "title_contains": []})
        lay.setdefault("pages", [])
        for page in lay["pages"]:
            page.setdefault("id", _gen_id(page.get("name", "page")))
            page.setdefault("name", page["id"])
            for slot in page.get("slots", []):
                _normalize_slot(slot)
            page.setdefault("icon", "📄")
            page.setdefault("slots", [])
    for page in data["global_pages"]:
        page.setdefault("id", _gen_id(page.get("name", "page")))
        page.setdefault("name", page["id"])
        page.setdefault("icon", "📄")
        page.setdefault("slots", [])
    return data


def _repair_misplaced_layouts(data: dict) -> bool:
    """Move layouts written into global_pages by the old add_layout handler."""
    layouts = data.setdefault("layouts", [])
    global_pages = data.setdefault("global_pages", [])
    existing_ids = {str(item.get("id")) for item in layouts if isinstance(item, dict)}
    repaired = False
    remaining = []
    for item in global_pages:
        if isinstance(item, dict) and isinstance(item.get("pages"), list):
            layout_id = str(item.get("id") or _gen_id(item.get("name", "layout")))
            item["id"] = layout_id
            item.pop("slots", None)
            if layout_id not in existing_ids:
                layouts.append(item)
                existing_ids.add(layout_id)
            repaired = True
        else:
            remaining.append(item)
    if repaired:
        data["global_pages"] = remaining
    return repaired


def _normalize_slot(slot: dict) -> None:
    """把 slot 的 row/col span 字段标准化。旧 span 字段兼容为 colspan。"""
    slot.setdefault("rowspan", 1)
    slot.setdefault("colspan", 1)
    # 兼容旧 V1/V2 数据：旧 span 字段当 colspan（强制覆盖 setdefault 的 1）
    if "span" in slot:
        try:
            slot["colspan"] = max(1, int(slot.pop("span")))
        except Exception:
            slot.pop("span", None)
    # 数值类型兜底（json 加载后可能是 None 或 0）
    try:
        slot["rowspan"] = max(1, min(8, int(slot.get("rowspan") or 1)))
    except Exception:
        slot["rowspan"] = 1
    try:
        slot["colspan"] = max(1, min(8, int(slot.get("colspan") or 1)))
    except Exception:
        slot["colspan"] = 1


def set_slot_size(layout_id: str, page_id: str, slot_r: int, slot_c: int,
                  rowspan: int = 1, colspan: int = 1) -> bool:
    """调整 slot 的大小。会自动从被覆盖的格子（如果有冲突数据）修复。"""
    rowspan = max(1, min(8, int(rowspan)))
    colspan = max(1, min(8, int(colspan)))
    with _file_lock_acquire() as fd:
        data = _load_unlocked()
        lay = find_layout(data, layout_id)
        if not lay: return False
        page = find_page(data, layout_id, page_id)
        if not page: return False
        slot = None
        for s in page.get("slots", []):
            if s.get("r") == slot_r and s.get("c") == slot_c:
                slot = s
                break
        if not slot: return False
        slot["rowspan"] = rowspan
        slot["colspan"] = colspan
        _normalize_slot(slot)
        ok = save(data)
    return ok



def save(data: dict) -> bool:
    """原子写：写 .tmp + fsync + os.replace。失败时保留旧文件。"""
    with _WRITE_LOCK:
        try:
            fd_lock = _file_lock_acquire()
        except Exception as e:
            print("[layouts] file lock failed:", e, flush=True)
            return False
        try:
            out_path = _layouts_path(write=True)
            tmp_path = out_path + ".tmp"
            # 写临时文件 + fsync
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except OSError:
                    pass
            # roundtrip 校验（避免序列化错误）
            try:
                with open(tmp_path, "r", encoding="utf-8") as f:
                    json.load(f)
            except Exception as e:
                os.remove(tmp_path)
                print("[layouts] save roundtrip failed:", e, flush=True)
                return False
            # Back up the current file (last successful version).
            if os.path.exists(out_path):
                try:
                    import shutil
                    shutil.copy2(out_path, _backup_path())
                except Exception:
                    pass
            # Atomic replace.
            os.replace(tmp_path, out_path)
            return True
        except Exception as e:
            print("[layouts] save failed:", e, flush=True)
            # 清理残留 tmp
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            return False
        finally:
            _file_lock_release(fd_lock)


def load_presets() -> list:
    """列出所有预设（不一定是 built_in，UI 上让用户挑）。"""
    out = []
    presets_root = _presets_dir_path()
    if not os.path.isdir(presets_root):
        return out
    for fn in sorted(os.listdir(presets_root)):
        if not fn.endswith(".json"):
            continue
        try:
            with open(os.path.join(presets_root, fn), "r", encoding="utf-8") as f:
                p = json.load(f)
            p["_file"] = fn
            out.append(p)
        except Exception as e:
            print(f"[layouts] preset read fail {fn}:", e, flush=True)
    return out


# ===== 查询 =====

def find_layout(data: dict, layout_id: str):
    for lay in data["layouts"]:
        if lay["id"] == layout_id:
            return lay
    return None


def find_page(data: dict, layout_id: str, page_id: str):
    """先在 layout.pages 找，再在 global_pages 找。"""
    if layout_id == "__global__":
        for p in data.get("global_pages", []):
            if p["id"] == page_id:
                return p, None
        return None, None
    lay = find_layout(data, layout_id)
    if not lay:
        return None, None
    for p in lay.get("pages", []):
        if p["id"] == page_id:
            return p, lay
    return None, lay


# ===== CRUD =====

def update_layout_field(layout_id: str, field: str, value) -> bool:
    """改 layout 顶层字段（name/icon/grid_cols/active_*）。"""
    data = load()
    if layout_id != "__global__":
        lay = find_layout(data, layout_id)
        if not lay:
            return False
        if field in ("name", "icon", "match"):
            lay[field] = value
    if field == "active_layout_id":
        data["active_layout_id"] = value
    elif field == "active_page_id":
        data["active_page_id"] = value
    elif field == "grid_cols":
        try:
            data["grid_cols"] = int(value)
        except Exception:
            return False
    elif field == "grid_rows":
        try:
            data["grid_rows"] = int(value)
        except Exception:
            return False
    save(data)
    return True


def set_active(layout_id: str, page_id: str) -> bool:
    data = load()
    data["active_layout_id"] = layout_id
    data["active_page_id"] = page_id
    return save(data)


def add_page(layout_id: str, page: dict) -> dict:
    """新增一个 page 到指定 layout。返回新 page。"""
    data = load()
    page.setdefault("id", _gen_id(page.get("name", "page")))
    page.setdefault("name", page["id"])
    page.setdefault("icon", "📄")
    page.setdefault("slots", [])
    if layout_id == "__global__":
        data["global_pages"].append(page)
    else:
        lay = find_layout(data, layout_id)
        if not lay:
            return None
        lay["pages"].append(page)
    save(data)
    return page


def add_layout(layout: dict) -> dict:
    """Add a complete layout created on the phone."""
    if not isinstance(layout, dict):
        return None
    data = load()
    layout_id = str(layout.get("id") or _gen_id(layout.get("name", "layout")))
    if find_layout(data, layout_id):
        return None
    pages = layout.get("pages")
    if not isinstance(pages, list) or not pages:
        pages = [{"id": _gen_id("page"), "name": "页面 1", "icon": "📄", "slots": []}]
    normalized_pages = []
    for index, raw_page in enumerate(pages):
        page = dict(raw_page) if isinstance(raw_page, dict) else {}
        page["id"] = str(page.get("id") or _gen_id("page"))
        page["name"] = str(page.get("name") or ("页面 " + str(index + 1)))
        page.setdefault("icon", "📄")
        page["slots"] = list(page.get("slots") or [])
        normalized_pages.append(page)
    new_layout = {
        "id": layout_id,
        "name": str(layout.get("name") or "新方案"),
        "icon": str(layout.get("icon") or ""),
        "match": dict(layout.get("match") or {"process": [], "title_contains": []}),
        "pages": normalized_pages,
    }
    data.setdefault("layouts", []).append(new_layout)
    data["active_layout_id"] = layout_id
    data["active_page_id"] = normalized_pages[0]["id"]
    save(data)
    return new_layout


def _ensure_active_layout(data: dict) -> None:
    layouts = data.setdefault("layouts", [])
    if not layouts:
        stamp = secrets.token_hex(3)
        layouts.append({
            "id": "blank_" + stamp,
            "name": "空白方案",
            "icon": "",
            "match": {"process": [], "title_contains": []},
            "pages": [{"id": "page_" + stamp, "name": "页面 1", "icon": "📄", "slots": []}],
        })
    active = find_layout(data, str(data.get("active_layout_id") or ""))
    if not active:
        active = layouts[0]
        data["active_layout_id"] = active["id"]
    pages = active.get("pages") or []
    if not any(page.get("id") == data.get("active_page_id") for page in pages):
        data["active_page_id"] = pages[0]["id"] if pages else None


def delete_layout(layout_id: str) -> bool:
    data = load()
    before = len(data.get("layouts", []))
    data["layouts"] = [item for item in data.get("layouts", []) if item.get("id") != layout_id]
    if len(data["layouts"]) == before:
        return False
    _ensure_active_layout(data)
    return save(data)


def archive_layout(layout_id: str) -> bool:
    data = load()
    target = find_layout(data, layout_id)
    if not target:
        return False
    data["layouts"] = [item for item in data.get("layouts", []) if item.get("id") != layout_id]
    archived = data.setdefault("archived_layouts", [])
    archived[:] = [item for item in archived if item.get("id") != layout_id]
    archived.append(target)
    _ensure_active_layout(data)
    return save(data)


def restore_layout(layout_id: str) -> bool:
    data = load()
    archived = data.setdefault("archived_layouts", [])
    target = next((item for item in archived if item.get("id") == layout_id), None)
    if not target:
        return False
    archived.remove(target)
    if find_layout(data, layout_id):
        target["id"] = _gen_id(target.get("name", "layout"))
    data.setdefault("layouts", []).append(target)
    data["active_layout_id"] = target["id"]
    pages = target.get("pages") or []
    data["active_page_id"] = pages[0]["id"] if pages else None
    return save(data)


def delete_page(layout_id: str, page_id: str) -> bool:
    data = load()
    if layout_id == "__global__":
        before = len(data["global_pages"])
        data["global_pages"] = [p for p in data["global_pages"] if p["id"] != page_id]
        ok = len(data["global_pages"]) != before
    else:
        lay = find_layout(data, layout_id)
        if not lay:
            return False
        before = len(lay["pages"])
        lay["pages"] = [p for p in lay["pages"] if p["id"] != page_id]
        ok = len(lay["pages"]) != before
    save(data)
    return ok


def rename_page(layout_id: str, page_id: str, name: str, icon: str = None) -> bool:
    data = load()
    page, _ = find_page(data, layout_id, page_id)
    if not page:
        return False
    page["name"] = name
    if icon is not None:
        page["icon"] = icon
    save(data)
    return True


def add_slot(layout_id: str, page_id: str, slot: dict) -> dict:
    """新增槽位，自动找空位。slot 必须包含 key 字段。"""
    data = load()
    page, _ = find_page(data, layout_id, page_id)
    if not page:
        return None
    if not isinstance(slot, dict) or "key" not in slot:
        return None
    if not slot["key"].get("id"):
        slot["key"]["id"] = _gen_id(slot["key"].get("label", "key"))
    grid_cols = data.get("grid_cols", 4)
    r = slot.get("r")
    c = slot.get("c")
    needs_alloc = (
        r is None or c is None
        or not isinstance(r, int) or not isinstance(c, int)
        or r < 0 or c < 0
        or c >= grid_cols
        or any(s.get("r") == r and s.get("c") == c for s in page.get("slots", []))
    )
    if needs_alloc:
        r, c = _next_free_cell(page, grid_cols)
        slot["r"] = r
        slot["c"] = c
    slot.setdefault("span", 1)
    page.setdefault("slots", []).append(slot)
    save(data)
    return slot


def update_slot(layout_id: str, page_id: str, slot_r: int, slot_c: int, updates: dict) -> bool:
    """按 (r,c) 找槽位并应用 updates（支持改 key 字段、span、r、c）。"""
    data = load()
    page, _ = find_page(data, layout_id, page_id)
    if not page:
        return False
    for s in page.get("slots", []):
        if s.get("r") == slot_r and s.get("c") == slot_c:
            for k, v in updates.items():
                if k == "key" and isinstance(v, dict):
                    s.setdefault("key", {}).update(v)
                    if "id" not in s["key"] or not s["key"]["id"]:
                        s["key"]["id"] = _gen_id(s["key"].get("label", "key"))
                else:
                    s[k] = v
            save(data)
            return True
    return False


def delete_slot(layout_id: str, page_id: str, slot_r: int, slot_c: int) -> bool:
    data = load()
    page, _ = find_page(data, layout_id, page_id)
    if not page:
        return False
    before = len(page.get("slots", []))
    page["slots"] = [s for s in page.get("slots", []) if not (s.get("r") == slot_r and s.get("c") == slot_c)]
    ok = len(page["slots"]) != before
    save(data)
    return ok


def move_slot(layout_id: str, page_id: str, src: tuple, dst: tuple) -> bool:
    """把 (r,c) 槽位移到 (r,c)；如果目标位置已有内容则对调。"""
    if src == dst:
        return False  # 边界：源=目标 = noop
    if not (isinstance(src, (list, tuple)) and len(src) == 2 and isinstance(dst, (list, tuple)) and len(dst) == 2):
        return False
    if any((not isinstance(x, int)) or x < 0 for x in (*src, *dst)):
        return False
    data = load()
    page, _ = find_page(data, layout_id, page_id)
    if not page:
        return False
    slots = page.setdefault("slots", [])
    src_slot = None
    dst_slot = None
    for s in slots:
        if (s.get("r"), s.get("c")) == src:
            src_slot = s
        if (s.get("r"), s.get("c")) == dst:
            dst_slot = s
    if not src_slot:
        return False
    if dst_slot:
        dst_slot["r"], src_slot["r"] = src_slot["r"], dst_slot["r"]
        dst_slot["c"], src_slot["c"] = src_slot["c"], dst_slot["c"]
    else:
        src_slot["r"] = dst[0]
        src_slot["c"] = dst[1]
    save(data)
    return True


def _next_free_cell(page: dict, grid_cols: int) -> tuple:
    """找下一个空 (r, c)。"""
    used = {(s.get("r"), s.get("c")) for s in page.get("slots", [])}
    for r in range(50):
        for c in range(grid_cols):
            if (r, c) not in used:
                return r, c
    return 0, 0


# ===== 导入预设 =====

def install_preset(preset: dict, layout_id: str = None) -> dict:
    """把一个预设 layout 安装到当前数据。返回新 layout。"""
    data = load()
    new_layout = json.loads(json.dumps(preset))  # 深拷贝
    new_layout.pop("_file", None)
    new_layout.pop("built_in", None)
    target_id = layout_id or new_layout.get("id") or _gen_id(new_layout.get("name", "layout"))
    new_layout["id"] = target_id
    # 如果已存在同 id，覆盖；否则追加
    existing = find_layout(data, target_id)
    if existing:
        idx = data["layouts"].index(existing)
        data["layouts"][idx] = new_layout
    else:
        data["layouts"].append(new_layout)
    save(data)
    return new_layout


# ===== 兼容 V1 =====

def add_v1(spec: dict) -> bool:
    """兼容旧 add_custom_key 协议：在 default layout 的 custom page 加一个。"""
    data = load()
    lay = find_layout(data, "default")
    if not lay:
        data = _default_data()
        lay = find_layout(data, "default")
    page = None
    for p in lay["pages"]:
        if p["id"] == "custom":
            page = p
            break
    if not page:
        page = {"id": "custom", "name": "自定义", "icon": "⚡", "slots": []}
        lay["pages"].append(page)
    slot = {
        "r": 0, "c": 0, "span": 1,
        "key": _shortcut_key(
            key_id=spec.get("id") or _gen_id(spec.get("label", "key")),
            label=spec.get("label", "?"),
            sub="+".join(spec.get("modifiers", []) + [spec.get("key", "")]).upper(),
            modifiers=spec.get("modifiers", []),
            key=spec.get("key", ""),
        ),
    }
    r, c = _next_free_cell(page, data.get("grid_cols", 4))
    slot["r"], slot["c"] = r, c
    page.setdefault("slots", []).append(slot)
    save(data)
    return True


def update_v1(spec_id: str, updates: dict) -> bool:
    data = load()
    for lay in data["layouts"]:
        for page in lay["pages"]:
            for s in page.get("slots", []):
                if s.get("key", {}).get("id") == spec_id:
                    if "label" in updates:
                        s["key"]["label"] = updates["label"]
                    if "icon" in updates:
                        s["key"]["icon"] = updates["icon"]
                    if "modifiers" in updates or "key" in updates:
                        sc = s["key"].setdefault("shortcut", {"modifiers": [], "key": ""})
                        if "modifiers" in updates:
                            sc["modifiers"] = updates["modifiers"]
                        if "key" in updates:
                            sc["key"] = updates["key"]
                    save(data)
                    return True
    return False


def delete_v1(spec_id: str) -> bool:
    data = load()
    for lay in data["layouts"]:
        for page in lay["pages"]:
            before = len(page.get("slots", []))
            page["slots"] = [s for s in page.get("slots", []) if s.get("key", {}).get("id") != spec_id]
            if len(page["slots"]) != before:
                save(data)
                return True
    return False


# ===== 自测 =====

if __name__ == "__main__":
    data = load()
    print("layouts:", len(data["layouts"]))
    for lay in data["layouts"]:
        print(f"  - {lay['id']}: {lay['name']} ({len(lay['pages'])} pages)")
        for p in lay["pages"]:
            print(f"      * {p['id']}: {p['name']} ({len(p.get('slots', []))} slots)")
    print("global_pages:", len(data["global_pages"]))

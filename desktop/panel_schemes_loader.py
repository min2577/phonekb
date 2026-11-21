"""panel_schemes_loader.py - 面板方案 (PanelScheme) 与底部 Tab 配置的加载与 CRUD.

数据结构 (V1):
    {
        "schema_version": 1,
        "version": 1,
        "active_scheme_id": "dev",
        "schemes": [
            {
                "id": "dev",
                "name": "开发模式",
                "icon": "💻",
                "built_in": True,
                "components": [
                    {"id": "ti1", "type": "text-input", "order": 0, "enabled": True, "config": {}},
                ]
            }
        ],
        "tab_config": [
            {"id": "panel", "page": "panel", "label": "面板", "icon": "🎛", "order": 0, "enabled": True},
        ]
    }

设计原则:
    - 方案与 layout 正交:PanelScheme 只决定面板由哪些组件组成,按键网格的具体内容仍由 layouts.json 决定。
    - 触发方式:手动切换,active_scheme_id 由用户在面板顶部切换器选择。
    - 组件 type 注册在手机端 componentRegistry.js,新增组件不影响本文件。
    - 缺失字段自动补全;未知字段保留(向前兼容)。

V2 接口预留:
    - schema_version 字段为云端方案包同步做准备(账号系统上线后,本文件可整体序列化为方案包上传)。
"""
import json
import os
import secrets
import sys
import threading
import time

_DIR = os.path.dirname(os.path.abspath(__file__))
LOCK_FILE = os.path.join(_DIR, ".panel_schemes.lock")


def _is_frozen():
    return getattr(sys, "frozen", False)


def _exe_dir():
    if _is_frozen():
        return os.path.dirname(os.path.abspath(sys.executable))
    return None


def _write_root():
    exe = _exe_dir()
    return exe if exe else _DIR


def _read_roots():
    exe = _exe_dir()
    if exe:
        return [exe, _DIR]
    return [_DIR]


def _first_existing(name, *, is_dir=False):
    checker = os.path.isdir if is_dir else os.path.isfile
    for root in _read_roots():
        p = os.path.join(root, name)
        if checker(p):
            return p
    return None


def _path(*, write=False):
    if write:
        root = _write_root()
        path = os.path.join(root, "panel_schemes.json")
        os.makedirs(root, exist_ok=True)
        return path
    found = _first_existing("panel_schemes.json")
    if found:
        return found
    return os.path.join(_write_root(), "panel_schemes.json")


_WRITE_LOCK = threading.Lock()


def _file_lock_acquire(timeout=5.0):
    import msvcrt
    fd = os.open(LOCK_FILE, os.O_CREAT | os.O_RDWR, 0o600)
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


def _file_lock_release(fd):
    try:
        import msvcrt
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    except Exception:
        pass
    try:
        os.close(fd)
    except Exception:
        pass


# ===== ID 生成 =====


def _gen_id(label="scheme"):
    base = (label or "scheme").lower().strip() or "scheme"
    base = "".join(ch if ch.isalnum() else "_" for ch in base).strip("_") or "scheme"
    return base + "_" + secrets.token_hex(3)


# ===== 默认数据 =====


def _default_data():
    return {
        "schema_version": 1,
        "version": 1,
        "active_scheme_id": "dev",
        "schemes": [
            {
                "id": "dev",
                "name": "开发模式",
                "icon": "💻",
                "built_in": True,
                "components": [
                    {"id": "ti1", "type": "text-input",    "order": 0, "enabled": True,  "config": {}},
                    {"id": "kg1", "type": "key-grid",      "order": 1, "enabled": True,  "config": {}},
                    {"id": "mc1", "type": "mouse-control", "order": 2, "enabled": True,  "config": {}},
                ],
            },
            {
                "id": "presentation",
                "name": "演示模式",
                "icon": "🎤",
                "built_in": True,
                "components": [
                    {"id": "kg2", "type": "key-grid",      "order": 0, "enabled": True,  "config": {}},
                    {"id": "mc2", "type": "mouse-control", "order": 1, "enabled": False, "config": {}},
                ],
            },
            {
                "id": "minimal",
                "name": "极简模式",
                "icon": "✨",
                "built_in": True,
                "components": [
                    {"id": "kg3", "type": "key-grid",      "order": 0, "enabled": True,  "config": {}},
                ],
            },
        ],
        "tab_config": [
            {"id": "panel",    "page": "panel",    "label": "面板", "icon": "🎛", "order": 0, "enabled": True},
            {"id": "layout",   "page": "layout",   "label": "布局", "icon": "📐", "order": 1, "enabled": True},
            {"id": "devices",  "page": "devices",  "label": "设备", "icon": "📱", "order": 2, "enabled": True},
            {"id": "settings", "page": "settings", "label": "设置", "icon": "⚙",  "order": 3, "enabled": True},
        ],
    }


# ===== 加载 =====


def load():
    """加载 panel_schemes.json;不存在则用默认。"""
    p = _first_existing("panel_schemes.json")
    if p:
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "schemes" in data:
                return _normalize(data)
        except Exception as e:
            print("[panel_schemes] load failed:", e, flush=True)
    return _default_data()


def save(data):
    """原子写。失败时保留旧文件。"""
    with _WRITE_LOCK:
        try:
            fd_lock = _file_lock_acquire()
        except Exception as e:
            print("[panel_schemes] file lock failed:", e, flush=True)
            return False
        try:
            out_path = _path(write=True)
            tmp_path = out_path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except Exception:
                    pass
            try:
                if os.path.exists(out_path):
                    bak = out_path + ".bak"
                    try:
                        if os.path.exists(bak):
                            os.remove(bak)
                    except Exception:
                        pass
                    import shutil
                    shutil.copy2(out_path, bak)
            except Exception as e:
                print("[panel_schemes] backup failed:", e, flush=True)
            os.replace(tmp_path, out_path)
            return True
        except Exception as e:
            print("[panel_schemes] save failed:", e, flush=True)
            return False
        finally:
            _file_lock_release(fd_lock)


# ===== 标准化 =====


def _normalize_component(c):
    """容错:补全 component 缺失字段。未知 type 保留(交给前端注册表判断)。"""
    if not isinstance(c, dict):
        return None
    c.setdefault("id", _gen_id(c.get("type", "comp")))
    c.setdefault("type", "unknown")
    c.setdefault("order", 0)
    c.setdefault("enabled", True)
    c.setdefault("config", {})
    return c


def _normalize_scheme(s):
    if not isinstance(s, dict):
        return None
    s.setdefault("id", _gen_id(s.get("name")))
    s.setdefault("name", s["id"])
    s.setdefault("icon", "📋")
    s.setdefault("built_in", False)
    s.setdefault("components", [])
    s["components"] = [c for c in (_normalize_component(x) for x in s["components"]) if c]
    s["components"].sort(key=lambda c: c.get("order", 0))
    return s


def _normalize_tab_item(t):
    if not isinstance(t, dict):
        return None
    t.setdefault("id", _gen_id(t.get("page", "tab")))
    t.setdefault("page", t["id"])
    t.setdefault("label", t["id"])
    t.setdefault("icon", "")
    t.setdefault("order", 0)
    t.setdefault("enabled", True)
    return t


def _normalize(data):
    """补全字段 + 排序 + 修正 active_scheme_id。"""
    data.setdefault("schema_version", 1)
    data.setdefault("version", 1)
    data.setdefault("active_scheme_id", "dev")
    data.setdefault("schemes", [])
    data["schemes"] = [s for s in (_normalize_scheme(x) for x in data["schemes"]) if s]
    data.setdefault("tab_config", [])
    data["tab_config"] = [t for t in (_normalize_tab_item(x) for x in data["tab_config"]) if t]
    data["tab_config"].sort(key=lambda t: t.get("order", 0))
    ids = {s["id"] for s in data["schemes"]}
    if data["active_scheme_id"] not in ids:
        data["active_scheme_id"] = next(iter(ids), "dev")
    return data


# ===== 公共 API =====


def get_active_scheme():
    """返回当前激活方案(深拷贝)。"""
    data = load()
    aid = data.get("active_scheme_id")
    for s in data["schemes"]:
        if s["id"] == aid:
            return json.loads(json.dumps(s))
    if data["schemes"]:
        return json.loads(json.dumps(data["schemes"][0]))
    return None


def get_all_schemes():
    """返回所有方案列表(深拷贝)。"""
    return [json.loads(json.dumps(s)) for s in load()["schemes"]]


def get_tab_config():
    """返回启用的 Tab 配置(按 order 排序)。"""
    cfg = load().get("tab_config", [])
    return [json.loads(json.dumps(t)) for t in cfg if t.get("enabled", True)]


def get_full_tab_config():
    """返回完整 Tab 配置(含 disabled,供编辑页使用)。"""
    return [json.loads(json.dumps(t)) for t in load().get("tab_config", [])]


def set_active_scheme(scheme_id):
    data = load()
    ids = {s["id"] for s in data["schemes"]}
    if scheme_id not in ids:
        return False
    data["active_scheme_id"] = scheme_id
    return save(data)


def replace_schemes(schemes, active_scheme_id=None):
    """整体替换 schemes 列表。编辑页保存时调用。"""
    data = load()
    data["schemes"] = [_normalize_scheme(json.loads(json.dumps(s))) for s in schemes]
    if active_scheme_id:
        ids = {s["id"] for s in data["schemes"]}
        if active_scheme_id in ids:
            data["active_scheme_id"] = active_scheme_id
    return save(data)


def replace_tab_config(tab_config):
    """整体替换 tab_config。"""
    data = load()
    data["tab_config"] = [_normalize_tab_item(json.loads(json.dumps(t))) for t in tab_config]
    return save(data)


if __name__ == "__main__":
    d = load()
    print("active:", d.get("active_scheme_id"))
    print("schemes:", len(d.get("schemes", [])))
    print("tabs:", len([t for t in d.get("tab_config", []) if t.get("enabled")]))

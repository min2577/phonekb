"""Persistence for desktop applications explicitly authorized from the PC clipboard."""
import hashlib
import json
import os
import sys
import tempfile
import threading
from pathlib import Path


_LOCK = threading.Lock()


def _data_path() -> str:
    """Store mutable data beside the executable when running as a frozen app."""
    base = os.path.dirname(os.path.abspath(sys.executable)) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "authorized_apps.json")


REGISTRY_PATH = _data_path()


def _empty_registry() -> dict:
    return {"version": 1, "apps": {}}


def _load() -> dict:
    try:
        with open(REGISTRY_PATH, "r", encoding="utf-8") as file:
            data = json.load(file)
        if isinstance(data, dict) and isinstance(data.get("apps"), dict):
            data.setdefault("version", 1)
            return data
    except FileNotFoundError:
        pass
    except (OSError, json.JSONDecodeError):
        pass
    return _empty_registry()


def _save(data: dict) -> None:
    directory = os.path.dirname(REGISTRY_PATH) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix="authorized_apps_", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.flush()
            os.fsync(file.fileno())
        os.replace(tmp_path, REGISTRY_PATH)
    finally:
        try:
            os.remove(tmp_path)
        except FileNotFoundError:
            pass


def normalize_executable_path(value: str) -> tuple[str | None, str | None]:
    """Accept only a copied, existing Windows executable path."""
    if not isinstance(value, str):
        return None, "电脑剪贴板中没有可用路径"
    path = value.strip()
    if len(path) >= 2 and path[0] == path[-1] == '"':
        path = path[1:-1]
    if not path or len(path) > 32767 or "\x00" in path:
        return None, "软件路径无效"
    path = os.path.normpath(os.path.abspath(os.path.expandvars(os.path.expanduser(path))))
    if os.path.splitext(path)[1].lower() != ".exe":
        return None, "请先在电脑上复制 .exe 软件的路径"
    if not os.path.isfile(path):
        return None, "电脑上找不到这个软件，请重新复制路径"
    return os.path.realpath(path), None


def authorize_path(value: str) -> tuple[dict | None, str | None]:
    """Save a clipboard-selected executable and return its stable opaque id."""
    path, error = normalize_executable_path(value)
    if error:
        return None, error
    normalized = os.path.normcase(path)
    app_id = "app_" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    app = {"id": app_id, "name": Path(path).stem, "path": path}
    with _LOCK:
        data = _load()
        data["apps"][app_id] = app
        _save(data)
    return {"id": app_id, "name": app["name"]}, None


def get_app(app_id: str) -> dict | None:
    if not isinstance(app_id, str) or not app_id.startswith("app_") or len(app_id) > 80:
        return None
    with _LOCK:
        app = _load().get("apps", {}).get(app_id)
    if not isinstance(app, dict) or not isinstance(app.get("path"), str):
        return None
    return dict(app)

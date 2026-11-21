"""Run Codex CLI tasks and expose a small transport-neutral control protocol."""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Callable, Optional

import codex_desktop_binding
import codex_voice


log = logging.getLogger("phonekb.codex_bridge")

MAX_PROMPT_LENGTH = 8000
MAX_RESULT_LENGTH = 12000
VALID_REASONING = {"low", "medium", "high", "xhigh"}
WORKFLOW_PREFIXES = {
    "review": "请先审查当前项目的相关代码，指出风险和测试缺口，然后按任务要求处理。\n\n",
    "debug": "请先定位根因，再进行最小修复并运行相关验证。\n\n",
    "test": "请运行与任务相关的测试，分析失败原因并完成必要修复。\n\n",
    "refactor": "请保持现有行为，完成必要重构并运行相关验证。\n\n",
}
LAYOUT_CODEX_ACTIONS = {
    "focus_task": "codex_focus_slot",
    "approve": "codex_approve",
    "reject": "codex_reject",
}


def _data_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _project_root() -> Path:
    configured = os.environ.get("PHONEKB_CODEX_WORKSPACE")
    if configured:
        return Path(configured).expanduser().resolve()
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        candidates = [exe_dir, exe_dir.parent, exe_dir.parent.parent]
        for candidate in candidates:
            if (candidate / ".git").exists() or (candidate / "AGENTS.md").exists():
                return candidate
        return exe_dir
    return Path(__file__).resolve().parent.parent


def _script_codex_prefix(path: Path) -> Optional[list[str]]:
    """Resolve npm's .cmd/.ps1 launcher to node + codex.js for Popen."""
    script = path.parent / "node_modules" / "@openai" / "codex" / "bin" / "codex.js"
    node = path.parent / "node.exe"
    if not node.is_file():
        node_path = shutil.which("node")
        node = Path(node_path) if node_path else node
    if script.is_file() and node.is_file():
        return [str(node.resolve()), str(script.resolve())]
    return None


def _find_codex() -> Optional[list[str]]:
    configured = os.environ.get("CODEX_CLI_PATH")
    if configured and Path(configured).is_file():
        configured_path = Path(configured).resolve()
        if configured_path.suffix.lower() in {".cmd", ".ps1"}:
            return _script_codex_prefix(configured_path) or [str(configured_path)]
        return [str(configured_path)]

    # Prefer the signed CLI shipped with the Codex desktop app. Windows may
    # expose a Store execution alias earlier on PATH which cannot be launched
    # by a background process and returns WinError 5.
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        root = Path(local_app_data) / "OpenAI" / "Codex" / "bin"
        if root.exists():
            candidates = sorted(root.glob("*/codex.exe"), key=lambda path: path.stat().st_mtime, reverse=True)
            if candidates:
                return [str(candidates[0].resolve())]

    for name in ("codex", "codex.exe"):
        found = shutil.which(name)
        if not found:
            continue
        found_path = Path(found).resolve()
        if "WindowsApps" in str(found_path):
            continue
        if found_path.suffix.lower() in {".cmd", ".ps1"}:
            return _script_codex_prefix(found_path) or [str(found_path)]
        return [str(found_path)]
    return None


class CodexBridge:
    def __init__(
        self,
        state_path: Optional[Path] = None,
        codex_command: Optional[list[str]] = None,
        workspace: Optional[Path] = None,
        monitor_desktop: bool = False,
    ):
        self.state_path = Path(state_path or (_data_dir() / "codex_micro_state.json"))
        self.codex_command = list(codex_command) if codex_command else None
        self.workspace = Path(workspace or _project_root()).resolve()
        self._lock = threading.RLock()
        self._listeners: dict[str, Callable[[dict], None]] = {}
        self._tasks: dict[int, dict] = {}
        self._processes: dict[str, subprocess.Popen] = {}
        self._monitor_desktop = bool(monitor_desktop)
        self._desktop_monitor_started = False
        self._defaults = {"reasoning_effort": "high", "model": ""}
        self.desktop_bindings = codex_desktop_binding.CodexDesktopBindings(_data_dir() / "codex_desktop_bindings.json")
        self._load()

    def register_client(self, client_key: str, sender: Callable[[dict], None]) -> None:
        with self._lock:
            self._listeners[client_key] = sender
        if self._monitor_desktop:
            self._start_desktop_monitor()

    def unregister_client(self, client_key: str) -> None:
        with self._lock:
            self._listeners.pop(client_key, None)

    def handle_message(self, message: dict) -> dict:
        action = str(message.get("action", ""))
        if action == "codex_get_snapshot":
            return self.snapshot()
        if action == "codex_bind_current_slot":
            return self.desktop_bindings.bind_current(message.get("slot"))
        if action == "codex_focus_slot":
            result = self.desktop_bindings.focus(message.get("slot"))
            request_id = str(message.get("request_id") or "")
            if request_id:
                result["request_id"] = request_id
            return result
        if action == "codex_unbind_slot":
            return self.desktop_bindings.unbind(message.get("slot"))
        if action == "codex_rename_slot":
            return self.desktop_bindings.rename(message.get("slot"), message.get("title"))
        if action == "codex_set_desktop_reasoning":
            return self.desktop_bindings.set_reasoning(message.get("slot"), message.get("reasoning_effort"))
        if action == "codex_open_new_task":
            result = dict(codex_voice.open_new_task())
            result["action"] = "codex_open_new_task_ack"
            request_id = str(message.get("request_id") or "")
            if request_id:
                result["request_id"] = request_id
            return result
        if action == "codex_create":
            return self._create(message)
        if action == "codex_resume":
            return self._resume(message)
        if action == "codex_cancel":
            return self._cancel(message)
        if action == "codex_set_defaults":
            return self._set_defaults(message)
        if action in {"codex_approve", "codex_reject"}:
            decision = "approve" if action == "codex_approve" else "reject"
            result = self.desktop_bindings.resolve_approval(
                message.get("slot"),
                message.get("thread_id"),
                message.get("fingerprint"),
                decision,
            )
            if result.get("approval") is not None:
                self._broadcast({"action": "codex_approval_status", **dict(result.get("approval") or {})})
            return result
        return {"action": "codex_error", "ok": False, "msg": "unknown Codex action: " + action}

    def handle_layout_action(self, key: dict) -> dict:
        config = key.get("codex") if isinstance(key, dict) else None
        if not isinstance(config, dict):
            return {"ok": False, "msg": "Codex 按键配置缺失"}
        layout_action = str(config.get("action") or "")
        bridge_action = LAYOUT_CODEX_ACTIONS.get(layout_action)
        if not bridge_action:
            return {"ok": False, "msg": "不支持的 Codex 按键动作"}
        slot, error = self._validate_slot(config.get("slot"))
        if error:
            return {"ok": False, "msg": "Codex 任务槽必须是 1 到 6"}
        message = {"action": bridge_action, "slot": slot}
        if bridge_action in {"codex_approve", "codex_reject"}:
            approval = self.desktop_bindings.approval_status()
            message["thread_id"] = approval.get("thread_id")
            message["fingerprint"] = approval.get("fingerprint")
        result = dict(self.handle_message(message))
        result["layout_action"] = layout_action
        result["slot"] = slot
        if result.get("ok") and not result.get("msg"):
            success_labels = {
                "focus_task": "已切换到任务槽 " + str(slot),
                "approve": "已批准任务槽 " + str(slot) + " 的操作",
                "reject": "已拒绝任务槽 " + str(slot) + " 的操作",
            }
            result["msg"] = success_labels[layout_action]
        return result

    def handle_layout_long_action(self, key: dict) -> dict:
        failure_action = "codex_bind_current_slot_ack"
        config = key.get("codex") if isinstance(key, dict) else None
        if not isinstance(config, dict) or config.get("action") != "focus_task":
            return {"action": failure_action, "ok": False, "msg": "该 Codex 按键不支持长按绑定"}
        long_action = config.get("long_press_action")
        if long_action is None:
            long_action = "bind_current_task"
        if long_action != "bind_current_task":
            return {"action": failure_action, "ok": False, "msg": "该按键没有启用长按绑定"}
        slot, error = self._validate_slot(config.get("slot"))
        if error:
            return {"action": failure_action, "ok": False, "msg": "Codex 任务槽必须是 1 到 6"}
        result = dict(self.handle_message({"action": "codex_bind_current_slot", "slot": slot}))
        result["layout_long_action"] = long_action
        result["slot"] = slot
        return result

    def snapshot(self) -> dict:
        with self._lock:
            tasks = [self._public_task(self._task_for_slot(slot)) for slot in range(1, 7)]
            desktop_bindings = self.desktop_bindings.snapshot()
            return {
                "action": "codex_snapshot",
                "available": self._codex_available(),
                "workspace": str(self.workspace),
                "desktop_bindings": desktop_bindings,
                "approval": self.desktop_bindings.approval_status(),
                "defaults": dict(self._defaults),
                "tasks": tasks,
            }

    def _start_desktop_monitor(self) -> None:
        with self._lock:
            if self._desktop_monitor_started:
                return
            self._desktop_monitor_started = True

        def monitor() -> None:
            # Establish a baseline before clients receive events, so an old
            # completed task does not trigger a fresh completion notification.
            self.desktop_bindings.refresh_statuses()
            while True:
                time.sleep(0.8)
                try:
                    changed = self.desktop_bindings.refresh_statuses()
                    for binding in changed:
                        self._broadcast({
                            "action": "codex_binding_status",
                            "slot": binding.get("slot"),
                            "binding": binding,
                        })
                    approval = self.desktop_bindings.refresh_approval()
                    if approval is not None:
                        self._broadcast({"action": "codex_approval_status", **approval})
                except Exception:
                    log.warning("Codex Desktop status monitor failed", exc_info=True)

        threading.Thread(target=monitor, name="phonekb-codex-desktop-monitor", daemon=True).start()

    def wait_for_terminal(self, task_id: str, timeout: float = 120.0) -> Optional[dict]:
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._lock:
                task = self._find_task(task_id)
                if task and task.get("state") in {"completed", "failed", "cancelled"}:
                    return self._public_task(task)
            time.sleep(0.05)
        return None

    def _create(self, message: dict) -> dict:
        prompt, error = self._validate_prompt(message.get("prompt"))
        if error:
            return {"action": "codex_create_ack", "ok": False, "msg": error}
        slot, error = self._validate_slot(message.get("slot"))
        if error:
            return {"action": "codex_create_ack", "ok": False, "msg": error}

        reasoning = str(message.get("reasoning_effort") or self._defaults["reasoning_effort"])
        if reasoning not in VALID_REASONING:
            return {"action": "codex_create_ack", "ok": False, "msg": "invalid reasoning effort"}
        model = str(message.get("model") or self._defaults.get("model") or "").strip()
        workflow_id = str(message.get("workflow_id") or "").strip()
        full_prompt = WORKFLOW_PREFIXES.get(workflow_id, "") + prompt

        with self._lock:
            current = self._tasks.get(slot)
            if current and current.get("state") in {"starting", "running"}:
                return {"action": "codex_create_ack", "ok": False, "msg": "该任务槽正在运行"}
            task = self._new_task(slot, prompt, reasoning, model, workflow_id)
            self._tasks[slot] = task
            self._save_locked()

        command, error = self._build_command(full_prompt, reasoning, model)
        if error:
            self._fail_before_start(task, error)
            return {"action": "codex_create_ack", "ok": False, "msg": error, "task": self._public_task(task)}

        self._broadcast_status(task)
        worker = threading.Thread(target=self._run_task, args=(task, command), name="codex-slot-" + str(slot), daemon=True)
        worker.start()
        return {"action": "codex_create_ack", "ok": True, "task": self._public_task(task)}

    def _resume(self, message: dict) -> dict:
        prompt, error = self._validate_prompt(message.get("prompt"))
        if error:
            return {"action": "codex_resume_ack", "ok": False, "msg": error}
        slot, error = self._validate_slot(message.get("slot"))
        if error:
            return {"action": "codex_resume_ack", "ok": False, "msg": error}
        session_id = str(message.get("session_id") or "").strip()
        if not session_id:
            with self._lock:
                existing = self._tasks.get(slot)
                session_id = str((existing or {}).get("session_id") or "")
        if not session_id:
            return {"action": "codex_resume_ack", "ok": False, "msg": "该任务槽没有可恢复的 Codex 会话"}

        reasoning = str(message.get("reasoning_effort") or self._defaults["reasoning_effort"])
        model = str(message.get("model") or self._defaults.get("model") or "").strip()
        with self._lock:
            current = self._tasks.get(slot)
            if current and current.get("state") in {"starting", "running"}:
                return {"action": "codex_resume_ack", "ok": False, "msg": "该任务槽正在运行"}
            task = self._new_task(slot, prompt, reasoning, model, "")
            task["session_id"] = session_id
            task["name"] = (current or {}).get("name") or self._task_name(prompt)
            self._tasks[slot] = task
            self._save_locked()

        command, error = self._build_command(prompt, reasoning, model, session_id=session_id)
        if error:
            self._fail_before_start(task, error)
            return {"action": "codex_resume_ack", "ok": False, "msg": error, "task": self._public_task(task)}
        self._broadcast_status(task)
        threading.Thread(target=self._run_task, args=(task, command), name="codex-resume-" + str(slot), daemon=True).start()
        return {"action": "codex_resume_ack", "ok": True, "task": self._public_task(task)}

    def _cancel(self, message: dict) -> dict:
        task_id = str(message.get("task_id") or "").strip()
        slot = message.get("slot")
        with self._lock:
            task = self._find_task(task_id) if task_id else self._tasks.get(int(slot or 0))
            if not task:
                return {"action": "codex_cancel_ack", "ok": False, "msg": "任务不存在"}
            if task.get("state") not in {"starting", "running"}:
                return {"action": "codex_cancel_ack", "ok": False, "msg": "任务当前没有运行"}
            task["cancel_requested"] = True
            task["detail"] = "正在停止"
            process = self._processes.get(task["task_id"])
        if process and process.poll() is None:
            try:
                process.terminate()
            except Exception as exc:
                return {"action": "codex_cancel_ack", "ok": False, "msg": "停止失败: " + str(exc)}
        self._broadcast_status(task)
        return {"action": "codex_cancel_ack", "ok": True, "task": self._public_task(task)}

    def _set_defaults(self, message: dict) -> dict:
        reasoning = str(message.get("reasoning_effort") or self._defaults["reasoning_effort"])
        if reasoning not in VALID_REASONING:
            return {"action": "codex_defaults_ack", "ok": False, "msg": "invalid reasoning effort"}
        model = str(message.get("model") if message.get("model") is not None else self._defaults.get("model", "")).strip()
        with self._lock:
            self._defaults = {"reasoning_effort": reasoning, "model": model}
            self._save_locked()
        return {"action": "codex_defaults_ack", "ok": True, "defaults": dict(self._defaults)}

    def _run_task(self, task: dict, command: list[str]) -> None:
        output_lines: list[str] = []
        try:
            creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            process = subprocess.Popen(
                command,
                cwd=str(self.workspace),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=creation_flags,
            )
            with self._lock:
                self._processes[task["task_id"]] = process
                task["state"] = "running"
                task["detail"] = "Codex 正在处理"
                task["updated_at"] = self._now()
                self._save_locked()
            self._broadcast_status(task)

            assert process.stdout is not None
            with process.stdout:
                for raw_line in process.stdout:
                    line = raw_line.strip()
                    if not line:
                        continue
                    output_lines.append(line)
                    self._consume_event(task, line)
            return_code = process.wait()
            with self._lock:
                self._processes.pop(task["task_id"], None)
                if task.get("cancel_requested"):
                    task["state"] = "cancelled"
                    task["detail"] = "任务已停止"
                elif return_code == 0:
                    task["state"] = "completed"
                    task["detail"] = "Codex 已完成"
                else:
                    task["state"] = "failed"
                    task["detail"] = self._last_error(output_lines, return_code)
                task["updated_at"] = self._now()
                self._save_locked()
            self._broadcast_status(task)
            if task.get("state") == "completed":
                self._broadcast({"action": "codex_result", "task": self._public_task(task)})
        except Exception as exc:
            log.exception("Codex task failed")
            with self._lock:
                self._processes.pop(task["task_id"], None)
                task["state"] = "failed"
                task["detail"] = "无法运行 Codex: " + str(exc)
                task["updated_at"] = self._now()
                self._save_locked()
            self._broadcast_status(task)

    def _consume_event(self, task: dict, line: str) -> None:
        try:
            event = json.loads(line)
        except Exception:
            if "error" in line.lower():
                with self._lock:
                    task["detail"] = line[-240:]
                    task["updated_at"] = self._now()
            return

        event_type = str(event.get("type") or "")
        changed = False
        with self._lock:
            thread_id = event.get("thread_id")
            if event_type == "thread.started" and thread_id:
                task["session_id"] = str(thread_id)
                changed = True

            item = event.get("item") if isinstance(event.get("item"), dict) else {}
            item_type = str(item.get("type") or "")
            text = item.get("text")
            if item_type == "agent_message" and isinstance(text, str) and text.strip():
                task["result"] = text.strip()[-MAX_RESULT_LENGTH:]
                task["detail"] = "Codex 已生成回复"
                changed = True
            elif item_type in {"command_execution", "mcp_tool_call", "web_search"}:
                task["detail"] = "Codex 正在执行工具"
                changed = True
            elif event_type == "turn.started":
                task["detail"] = "Codex 正在思考"
                changed = True
            elif event_type in {"turn.failed", "error"}:
                error = event.get("error")
                task["detail"] = self._error_text(error or event)
                changed = True

            if changed:
                task["updated_at"] = self._now()
                self._save_locked()
        if changed:
            self._broadcast_status(task)

    def _build_command(
        self,
        prompt: str,
        reasoning: str,
        model: str,
        session_id: str = "",
    ) -> tuple[Optional[list[str]], Optional[str]]:
        if not self.workspace.is_dir():
            return None, "Codex 工作区不存在: " + str(self.workspace)
        prefix = list(self.codex_command or [])
        if not prefix:
            codex_path = _find_codex()
            if not codex_path:
                return None, "电脑上没有找到 Codex CLI"
            prefix = list(codex_path)
        command = prefix + ["-C", str(self.workspace), "-s", "workspace-write", "exec"]
        if session_id:
            command += ["resume", session_id]
        command += ["--json"]
        command += ["-c", 'model_reasoning_effort="' + reasoning + '"']
        if model:
            command += ["-m", model]
        command.append(prompt)
        return command, None

    def _new_task(self, slot: int, prompt: str, reasoning: str, model: str, workflow_id: str) -> dict:
        return {
            "slot": slot,
            "task_id": "phonekb-" + uuid.uuid4().hex,
            "session_id": "",
            "name": self._task_name(prompt),
            "state": "starting",
            "detail": "正在启动 Codex",
            "result": "",
            "reasoning_effort": reasoning,
            "model": model,
            "workflow_id": workflow_id,
            "updated_at": self._now(),
            "cancel_requested": False,
        }

    def _task_for_slot(self, slot: int) -> dict:
        return self._tasks.get(slot) or {
            "slot": slot,
            "task_id": "",
            "session_id": "",
            "name": "空任务槽",
            "state": "idle",
            "detail": "点击新任务开始",
            "result": "",
            "reasoning_effort": self._defaults["reasoning_effort"],
            "model": self._defaults.get("model", ""),
            "workflow_id": "",
            "updated_at": "",
        }

    def _public_task(self, task: dict) -> dict:
        allowed = (
            "slot", "task_id", "session_id", "name", "state", "detail", "result",
            "reasoning_effort", "model", "workflow_id", "updated_at",
        )
        return {key: task.get(key, "") for key in allowed}

    def _broadcast_status(self, task: dict) -> None:
        self._broadcast({"action": "codex_status", "task": self._public_task(task)})

    def _broadcast(self, message: dict) -> None:
        with self._lock:
            listeners = list(self._listeners.items())
        for client_key, sender in listeners:
            try:
                sender(message)
            except Exception:
                log.warning("Dropping failed Codex listener: %s", client_key, exc_info=True)
                self.unregister_client(client_key)

    def _fail_before_start(self, task: dict, detail: str) -> None:
        with self._lock:
            task["state"] = "failed"
            task["detail"] = detail
            task["updated_at"] = self._now()
            self._save_locked()
        self._broadcast_status(task)

    def _find_task(self, task_id: str) -> Optional[dict]:
        for task in self._tasks.values():
            if task.get("task_id") == task_id:
                return task
        return None

    @staticmethod
    def _validate_prompt(value) -> tuple[Optional[str], Optional[str]]:
        prompt = str(value or "").strip()
        if not prompt:
            return None, "请输入要交给 Codex 的任务"
        if len(prompt) > MAX_PROMPT_LENGTH:
            return None, "任务内容过长"
        return prompt, None

    @staticmethod
    def _validate_slot(value) -> tuple[Optional[int], Optional[str]]:
        try:
            slot = int(value)
        except Exception:
            return None, "invalid task slot"
        if slot < 1 or slot > 6:
            return None, "invalid task slot"
        return slot, None

    @staticmethod
    def _task_name(prompt: str) -> str:
        compact = " ".join(prompt.split())
        return compact[:18] + ("..." if len(compact) > 18 else "")

    @staticmethod
    def _now() -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    @staticmethod
    def _error_text(error) -> str:
        if isinstance(error, dict):
            return str(error.get("message") or error.get("code") or error)[:300]
        return str(error)[:300]

    @staticmethod
    def _last_error(lines: list[str], return_code: int) -> str:
        for line in reversed(lines[-20:]):
            try:
                event = json.loads(line)
                if event.get("type") in {"turn.failed", "error"}:
                    return CodexBridge._error_text(event.get("error") or event)
            except Exception:
                if line:
                    return line[-300:]
        return "Codex 退出，代码 " + str(return_code)

    def _codex_available(self) -> bool:
        return bool(self.codex_command or _find_codex()) and self.workspace.is_dir()

    def _load(self) -> None:
        try:
            if not self.state_path.is_file():
                return
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
            defaults = raw.get("defaults") if isinstance(raw.get("defaults"), dict) else {}
            reasoning = str(defaults.get("reasoning_effort") or "high")
            self._defaults = {
                "reasoning_effort": reasoning if reasoning in VALID_REASONING else "high",
                "model": str(defaults.get("model") or ""),
            }
            for item in raw.get("tasks") or []:
                if not isinstance(item, dict):
                    continue
                slot = int(item.get("slot") or 0)
                if slot < 1 or slot > 6:
                    continue
                task = dict(item)
                if task.get("state") in {"starting", "running"}:
                    task["state"] = "failed"
                    task["detail"] = "电脑端重启，原任务已中断"
                task["cancel_requested"] = False
                self._tasks[slot] = task
        except Exception:
            log.warning("Failed to load Codex state", exc_info=True)

    def _save_locked(self) -> None:
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "version": 1,
                "workspace": str(self.workspace),
                "defaults": dict(self._defaults),
                "tasks": [self._public_task(task) for _, task in sorted(self._tasks.items())],
            }
            temp_path = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
            temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(temp_path, self.state_path)
        except Exception:
            log.warning("Failed to save Codex state", exc_info=True)


bridge = CodexBridge(monitor_desktop=True)


def register_client(client_key: str, sender: Callable[[dict], None]) -> None:
    bridge.register_client(client_key, sender)


def unregister_client(client_key: str) -> None:
    bridge.unregister_client(client_key)


def handle_message(message: dict) -> dict:
    return bridge.handle_message(message)


def handle_layout_action(key: dict) -> dict:
    return bridge.handle_layout_action(key)


def handle_layout_long_action(key: dict) -> dict:
    return bridge.handle_layout_long_action(key)


def snapshot() -> dict:
    return bridge.snapshot()

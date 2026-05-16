#!/usr/bin/env python3
"""
plato_room_ide.py — PLATO Agentic IDE: Rooms as Live Agent Workspaces
=====================================================================

PLATO rooms aren't just storage — they're live workspaces where agents operate.
Prompt a room and it executes as if it were any agent. Send it on a task and
come back later. Scroll up to see what happened. Diff to see what changed.

Architecture:
  AgentRoom  — a room that IS an agent workspace (state, shell, sandbox, history)
  RoomTask   — dispatch a room to work autonomously (loop until done)
  RoomDiff   — track file changes in room sandbox (snapshot/diff)
  RoomHistory — scrollable action log (every execute, write, response)
  AgentShell — configurable agent backend (DeepInfra, custom)
  RoomIDE    — the full IDE experience (create, enter, prompt, scroll, diff, dispatch)

REST API mountable on PLATO server (:8848/ide/*).

Usage:
    from plato_room_ide import RoomIDE
    ide = RoomIDE()
    room = ide.create_room("research", shell_type="seed-mini")
    ide.enter(room.room_id)
    ide.prompt("Analyze the constraint matrix for drift")
    ide.scroll(10)
    ide.diff()
    ide.leave()
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlparse, parse_qs

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEEPINFRA_KEY_PATH = Path.home() / ".openclaw" / "workspace" / ".credentials" / "deepinfra-api-key.txt"
SANDBOX_BASE = Path.home() / ".openclaw" / "workspace" / ".plato-ide-sandboxes"

SHELL_MODELS = {
    "seed-mini": "ByteDance/Seed-2.0-mini",
    "seed-code": "ByteDance/Seed-2.0-code",
    "hermes-70b": "NousResearch/Hermes-3-Llama-3.1-70B",
    "hermes-405b": "NousResearch/Hermes-3-Llama-3.1-405B",
    "qwen-235b": "Qwen/Qwen3-235B-A22B-Instruct-2507",
    "qwen-35b": "Qwen/Qwen3.6-35B-A3B",
    "custom": None,
}

DEEPINFRA_ENDPOINT = "https://api.deepinfra.com/v1/openai/chat/completions"


# ---------------------------------------------------------------------------
# RoomHistory — scrollable action log
# ---------------------------------------------------------------------------

@dataclass
class HistoryEntry:
    """A single entry in the room action log."""
    entry_id: str = ""
    timestamp: float = 0.0
    action: str = ""         # "execute", "write_file", "agent_response", "checkpoint", "error"
    summary: str = ""
    detail: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.entry_id:
            self.entry_id = uuid.uuid4().hex[:12]
        if not self.timestamp:
            self.timestamp = time.time()

    def format(self) -> str:
        ts = time.strftime("%H:%M:%S", time.localtime(self.timestamp))
        return f"[{ts}] {self.action} → {self.summary}"

    def to_dict(self) -> dict:
        return asdict(self)


class RoomHistory:
    """Scrollable action log for a room. Every action is recorded."""

    def __init__(self):
        self._entries: List[HistoryEntry] = []

    def log(self, action: str, summary: str, detail: Optional[dict] = None) -> HistoryEntry:
        entry = HistoryEntry(action=action, summary=summary, detail=detail or {})
        self._entries.append(entry)
        return entry

    def scroll(self, n: int = 20) -> List[HistoryEntry]:
        """Show last N entries."""
        return self._entries[-n:]

    def scroll_formatted(self, n: int = 20) -> List[str]:
        """Show last N entries formatted as strings."""
        return [e.format() for e in self.scroll(n)]

    def search(self, query: str) -> List[HistoryEntry]:
        """Find entries matching query in action or summary."""
        q = query.lower()
        return [e for e in self._entries if q in e.action.lower() or q in e.summary.lower()]

    def since(self, timestamp: float) -> List[HistoryEntry]:
        """Everything after a point in time."""
        return [e for e in self._entries if e.timestamp > timestamp]

    def all_entries(self) -> List[HistoryEntry]:
        return list(self._entries)

    @property
    def count(self) -> int:
        return len(self._entries)


# ---------------------------------------------------------------------------
# RoomDiff — track file changes in sandbox
# ---------------------------------------------------------------------------

@dataclass
class FileSnapshot:
    """Snapshot of a single file."""
    path: str
    hash: str
    size: int
    modified: float


@dataclass
class DiffResult:
    """Result of comparing two snapshots."""
    files_added: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    files_removed: List[str] = field(default_factory=list)
    content_diffs: Dict[str, Dict[str, str]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def has_changes(self) -> bool:
        return bool(self.files_added or self.files_modified or self.files_removed)


class RoomDiff:
    """Track changes in a room sandbox directory."""

    def __init__(self, sandbox_dir: Path):
        self.sandbox_dir = sandbox_dir
        self._checkpoints: Dict[str, Dict[str, FileSnapshot]] = {}
        self._initial_snapshot: Optional[Dict[str, FileSnapshot]] = None

    def snapshot(self) -> Dict[str, FileSnapshot]:
        """Capture current file state of sandbox."""
        files = {}
        if not self.sandbox_dir.exists():
            return files
        for fp in self.sandbox_dir.rglob("*"):
            if fp.is_file():
                rel = str(fp.relative_to(self.sandbox_dir))
                try:
                    content = fp.read_bytes()
                    h = hashlib.sha256(content).hexdigest()[:16]
                    files[rel] = FileSnapshot(
                        path=rel, hash=h,
                        size=len(content), modified=fp.stat().st_mtime,
                    )
                except (OSError, PermissionError):
                    continue
        return files

    def save_checkpoint(self, name: str) -> Dict[str, FileSnapshot]:
        """Save a named checkpoint of current file state."""
        snap = self.snapshot()
        self._checkpoints[name] = snap
        if self._initial_snapshot is None:
            self._initial_snapshot = snap
        return snap

    def diff(self, from_checkpoint: Optional[str] = None) -> DiffResult:
        """Show changes since checkpoint (or initial snapshot if None)."""
        if from_checkpoint:
            before = self._checkpoints.get(from_checkpoint, {})
        else:
            before = self._initial_snapshot or {}

        after = self.snapshot()
        result = DiffResult()

        before_paths = set(before.keys())
        after_paths = set(after.keys())

        result.files_added = sorted(after_paths - before_paths)
        result.files_removed = sorted(before_paths - after_paths)

        for p in before_paths & after_paths:
            if before[p].hash != after[p].hash:
                result.files_modified.append(p)
                # Read current and previous content for diff
                try:
                    current = (self.sandbox_dir / p).read_text(errors="replace")
                    result.content_diffs[p] = {
                        "current_hash": after[p].hash,
                        "previous_hash": before[p].hash,
                        "current_size": after[p].size,
                        "previous_size": before[p].size,
                        "preview": current[:500] if len(current) > 500 else current,
                    }
                except (OSError, UnicodeDecodeError):
                    result.content_diffs[p] = {
                        "current_hash": after[p].hash,
                        "previous_hash": before[p].hash,
                    }

        return result

    @property
    def checkpoints(self) -> List[str]:
        return list(self._checkpoints.keys())


# ---------------------------------------------------------------------------
# AgentShell — configurable agent backend
# ---------------------------------------------------------------------------

@dataclass
class ShellConfig:
    """Configuration for an agent shell."""
    shell_type: str = "seed-mini"
    model: str = ""
    temperature: float = 0.3
    max_tokens: int = 4096
    system_prompt: str = "You are a helpful agent working in a PLATO room workspace."
    api_key: str = ""

    def __post_init__(self):
        if not self.model and self.shell_type in SHELL_MODELS:
            self.model = SHELL_MODELS[self.shell_type] or "ByteDance/Seed-2.0-mini"
        if not self.api_key:
            self._load_key()

    def _load_key(self):
        if DEEPINFRA_KEY_PATH.exists():
            self.api_key = DEEPINFRA_KEY_PATH.read_text().strip()


class AgentShell:
    """Configurable agent backend. Calls DeepInfra API for execution."""

    def __init__(self, config: Optional[ShellConfig] = None):
        self.config = config or ShellConfig()
        self._conversation: List[Dict[str, str]] = []

    def execute(self, prompt: str, context: Optional[str] = None) -> str:
        """Execute a prompt through the agent shell. Returns response text."""
        messages = [{"role": "system", "content": self.config.system_prompt}]

        # Add conversation history (last 10 exchanges)
        messages.extend(self._conversation[-20:])

        # Add context if provided
        if context:
            messages.append({"role": "system", "content": f"Context:\n{context}"})

        messages.append({"role": "user", "content": prompt})

        try:
            import urllib.request
            import urllib.error

            payload = json.dumps({
                "model": self.config.model,
                "messages": messages,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
            }).encode()

            req = urllib.request.Request(
                DEEPINFRA_ENDPOINT,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.config.api_key}",
                },
            )

            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode())
                content = data["choices"][0]["message"]["content"]

                # Track conversation
                self._conversation.append({"role": "user", "content": prompt})
                self._conversation.append({"role": "assistant", "content": content})

                return content

        except Exception as e:
            return f"[Shell Error: {type(e).__name__}: {e}]"

    def swap_shell(self, shell_type: str, **kwargs) -> None:
        """Swap the agent shell mid-conversation (change agent without losing room state)."""
        self.config.shell_type = shell_type
        if shell_type in SHELL_MODELS:
            new_model = SHELL_MODELS[shell_type]
            if new_model:
                self.config.model = new_model
        for k, v in kwargs.items():
            if hasattr(self.config, k):
                setattr(self.config, k, v)

    def clear_conversation(self):
        """Clear conversation history."""
        self._conversation.clear()

    @property
    def conversation_length(self) -> int:
        return len(self._conversation)

    def to_dict(self) -> dict:
        return {
            "shell_type": self.config.shell_type,
            "model": self.config.model,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "conversation_turns": len(self._conversation) // 2,
            "system_prompt": self.config.system_prompt[:100] + "..." if len(self.config.system_prompt) > 100 else self.config.system_prompt,
        }


# ---------------------------------------------------------------------------
# AgentRoom — a room that IS an agent workspace
# ---------------------------------------------------------------------------

@dataclass
class RoomCheckpoint:
    """A named checkpoint of room state."""
    name: str
    timestamp: float
    file_snapshot_name: str
    history_length: int


class AgentRoom:
    """A PLATO room that is a live agent workspace."""

    def __init__(
        self,
        name: str,
        shell_type: str = "seed-mini",
        shell_config: Optional[ShellConfig] = None,
        room_id: Optional[str] = None,
    ):
        self.room_id = room_id or uuid.uuid4().hex[:12]
        self.name = name
        self.created_at = time.time()
        self.last_active = time.time()

        # Sandbox — isolated file area
        self.sandbox_dir = SANDBOX_BASE / self.room_id
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)

        # History
        self.history = RoomHistory()

        # Diff tracker
        self.diff_tracker = RoomDiff(self.sandbox_dir)

        # Agent shell
        config = shell_config or ShellConfig(shell_type=shell_type)
        self.shell = AgentShell(config)

        # Room state
        self._env: Dict[str, str] = {}
        self._checkpoints: Dict[str, RoomCheckpoint] = {}
        self._files_meta: Dict[str, Dict[str, Any]] = {}

        # Initial snapshot
        self.diff_tracker.save_checkpoint("__initial__")
        self.history.log("room_created", f"Room '{name}' created with shell {shell_type}")

    def touch(self):
        self.last_active = time.time()

    def execute(self, prompt: str, context: Optional[str] = None) -> str:
        """Send prompt to room's agent shell, log result."""
        self.touch()
        self.history.log("execute", prompt[:200], {"prompt": prompt, "context": context[:100] if context else None})

        response = self.shell.execute(prompt, context)

        self.history.log("agent_response", response[:200], {"response_length": len(response)})
        return response

    def write_file(self, filename: str, content: str) -> str:
        """Write a file to the room sandbox."""
        self.touch()
        filepath = self.sandbox_dir / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content)

        self._files_meta[filename] = {
            "size": len(content),
            "hash": hashlib.sha256(content.encode()).hexdigest()[:16],
            "written_at": time.time(),
        }
        self.history.log("write_file", f"Wrote {filename} ({len(content)} bytes)", {"filename": filename})
        return filename

    def read_file(self, filename: str) -> Optional[str]:
        """Read a file from the room sandbox."""
        filepath = self.sandbox_dir / filename
        if filepath.exists():
            return filepath.read_text()
        return None

    def list_files(self) -> List[Dict[str, Any]]:
        """List all files in sandbox with metadata."""
        files = []
        if not self.sandbox_dir.exists():
            return files
        for fp in sorted(self.sandbox_dir.rglob("*")):
            if fp.is_file():
                rel = str(fp.relative_to(self.sandbox_dir))
                stat = fp.stat()
                files.append({
                    "name": rel,
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                })
        return files

    def scroll(self, n: int = 20) -> List[str]:
        """Show last N actions in the room."""
        return self.history.scroll_formatted(n)

    def diff(self, since: Optional[str] = None) -> DiffResult:
        """Show what changed since checkpoint."""
        return self.diff_tracker.diff(since)

    def checkpoint(self, name: Optional[str] = None) -> str:
        """Save current state as a named checkpoint."""
        cp_name = name or f"cp-{len(self._checkpoints)}"
        self.diff_tracker.save_checkpoint(cp_name)
        cp = RoomCheckpoint(
            name=cp_name,
            timestamp=time.time(),
            file_snapshot_name=cp_name,
            history_length=self.history.count,
        )
        self._checkpoints[cp_name] = cp
        self.history.log("checkpoint", f"Checkpoint '{cp_name}' saved", {"checkpoint": cp_name})
        return cp_name

    def set_env(self, key: str, value: str):
        """Set an environment variable for the room."""
        self._env[key] = value
        self.history.log("set_env", f"{key}={value}", {"key": key})

    def get_env(self, key: str) -> Optional[str]:
        return self._env.get(key)

    def destroy(self):
        """Clean up sandbox directory."""
        if self.sandbox_dir.exists():
            shutil.rmtree(self.sandbox_dir, ignore_errors=True)

    def to_dict(self) -> dict:
        return {
            "room_id": self.room_id,
            "name": self.name,
            "created_at": self.created_at,
            "last_active": self.last_active,
            "shell": self.shell.to_dict(),
            "files": len(self.list_files()),
            "history_count": self.history.count,
            "checkpoints": list(self._checkpoints.keys()),
            "env_keys": list(self._env.keys()),
        }


# ---------------------------------------------------------------------------
# RoomTask — dispatch a room to work autonomously
# ---------------------------------------------------------------------------

@dataclass
class TaskStatus:
    """Status of a dispatched room task."""
    task_id: str
    room_id: str
    prompt: str
    status: str = "pending"  # pending, running, done, failed, killed
    max_iterations: int = 10
    current_iteration: int = 0
    result: str = ""
    results: List[str] = field(default_factory=list)
    started_at: float = 0.0
    finished_at: float = 0.0
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class RoomTask:
    """Dispatch a room to work autonomously on a task."""

    def __init__(
        self,
        room: AgentRoom,
        prompt: str,
        max_iterations: int = 10,
        task_id: Optional[str] = None,
    ):
        self.task_id = task_id or uuid.uuid4().hex[:12]
        self.room = room
        self.prompt = prompt
        self.max_iterations = max_iterations
        self._status = TaskStatus(
            task_id=self.task_id,
            room_id=room.room_id,
            prompt=prompt,
            max_iterations=max_iterations,
        )
        self._thread: Optional[threading.Thread] = None
        self._kill_flag = threading.Event()

    def run(self, background: bool = False) -> TaskStatus:
        """Execute the prompt in a loop until done or max_iterations.

        Each iteration:
        1. Send the prompt (or follow-up) to the room's shell
        2. Check if the response indicates completion
        3. If not done, generate a follow-up prompt
        """
        self._status.status = "running"
        self._status.started_at = time.time()

        if background:
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
        else:
            self._run_loop()

        return self._status

    def _run_loop(self):
        """Main task execution loop."""
        current_prompt = self.prompt

        for i in range(self.max_iterations):
            if self._kill_flag.is_set():
                self._status.status = "killed"
                self._status.finished_at = time.time()
                return

            self._status.current_iteration = i + 1

            try:
                response = self.room.execute(current_prompt)

                self._status.results.append(response)
                self._status.result = response

                # Check if the task is done (heuristic: response contains completion signals)
                if self._is_done(response):
                    self._status.status = "done"
                    self._status.finished_at = time.time()
                    return

                # Generate follow-up
                current_prompt = (
                    f"Continue working on: {self.prompt}\n\n"
                    f"Previous output (iteration {i+1}): {response[:500]}\n\n"
                    f"If complete, respond with DONE followed by your summary. "
                    f"Otherwise continue. Iteration {i+1}/{self.max_iterations}."
                )

            except Exception as e:
                self._status.status = "failed"
                self._status.error = str(e)
                self._status.finished_at = time.time()
                return

        # Exhausted iterations
        self._status.status = "done"
        self._status.finished_at = time.time()

    def _is_done(self, response: str) -> bool:
        """Check if the response indicates task completion."""
        done_signals = ["DONE", "COMPLETE", "FINISHED", "TASK COMPLETE", "[DONE]"]
        upper = response.upper()
        return any(sig in upper for sig in done_signals)

    def status(self) -> TaskStatus:
        return self._status

    def kill(self):
        """Stop the task."""
        self._kill_flag.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        if self._status.status == "running":
            self._status.status = "killed"
            self._status.finished_at = time.time()

    def to_dict(self) -> dict:
        return self._status.to_dict()


# ---------------------------------------------------------------------------
# RoomIDE — the full IDE experience
# ---------------------------------------------------------------------------

class RoomIDE:
    """The full PLATO Agentic IDE experience."""

    def __init__(self):
        self._rooms: Dict[str, AgentRoom] = {}
        self._tasks: Dict[str, RoomTask] = {}
        self._current_room: Optional[str] = None

    def create_room(
        self,
        name: str,
        shell_type: str = "seed-mini",
        shell_config: Optional[ShellConfig] = None,
    ) -> AgentRoom:
        """Create a new agent workspace room."""
        room = AgentRoom(name=name, shell_type=shell_type, shell_config=shell_config)
        self._rooms[room.room_id] = room
        return room

    def list_rooms(self) -> List[dict]:
        """List all active rooms with status."""
        return [room.to_dict() for room in self._rooms.values()]

    def get_room(self, room_id: str) -> Optional[AgentRoom]:
        """Get a room by ID."""
        return self._rooms.get(room_id)

    def enter(self, room_id: str) -> Optional[AgentRoom]:
        """Attach to a room (like entering the Construct)."""
        room = self._rooms.get(room_id)
        if room:
            self._current_room = room_id
            room.touch()
        return room

    def leave(self) -> Optional[str]:
        """Detach from current room (it keeps running)."""
        old = self._current_room
        self._current_room = None
        return old

    def prompt(self, text: str, context: Optional[str] = None) -> Optional[str]:
        """Send command to current room."""
        if not self._current_room:
            return None
        room = self._rooms.get(self._current_room)
        if not room:
            return None
        return room.execute(text, context)

    def scroll(self, n: int = 20) -> List[str]:
        """Review history of current room."""
        if not self._current_room:
            return []
        room = self._rooms.get(self._current_room)
        if not room:
            return []
        return room.scroll(n)

    def diff(self, since: Optional[str] = None) -> Optional[DiffResult]:
        """See what changed in current room."""
        if not self._current_room:
            return None
        room = self._rooms.get(self._current_room)
        if not room:
            return None
        return room.diff(since)

    def dispatch(self, room_id: str, task: str, max_iterations: int = 10, background: bool = True) -> Optional[RoomTask]:
        """Send room on autonomous task."""
        room = self._rooms.get(room_id)
        if not room:
            return None
        task_obj = RoomTask(room=room, prompt=task, max_iterations=max_iterations)
        self._tasks[task_obj.task_id] = task_obj
        task_obj.run(background=background)
        return task_obj

    def check(self, room_id: str) -> Optional[dict]:
        """Quick status of dispatched task for a room."""
        for task in self._tasks.values():
            if task.room.room_id == room_id:
                return task.to_dict()
        return None

    def get_task(self, task_id: str) -> Optional[RoomTask]:
        return self._tasks.get(task_id)

    def kill_task(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task:
            task.kill()
            return True
        return False

    def destroy_room(self, room_id: str) -> bool:
        """Remove a room and its sandbox."""
        room = self._rooms.pop(room_id, None)
        if room:
            room.destroy()
            if self._current_room == room_id:
                self._current_room = None
            return True
        return False

    @property
    def current_room_id(self) -> Optional[str]:
        return self._current_room


# ---------------------------------------------------------------------------
# REST API Handler — mountable on PLATO server
# ---------------------------------------------------------------------------

class RoomIDEHandler(BaseHTTPRequestHandler):
    """HTTP handler for PLATO Room IDE API."""

    ide: RoomIDE = None  # type: ignore

    def log_message(self, format, *args):
        if "200" not in str(args):
            super().log_message(format, *args)

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length))

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length)

    # ── GET routes ──────────────────────────────────────

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        params = parse_qs(parsed.query)

        if path == "/ide/rooms":
            self._send_json({"rooms": self.ide.list_rooms()})
        elif path.startswith("/ide/rooms/") and path.endswith("/scroll"):
            room_id = path.split("/")[3]
            n = int(params.get("n", ["20"])[0])
            room = self.ide.get_room(room_id)
            if room:
                entries = room.scroll(n)
                self._send_json({"entries": entries, "count": len(entries)})
            else:
                self._send_json({"error": "room not found"}, 404)
        elif path.startswith("/ide/rooms/") and path.endswith("/diff"):
            room_id = path.split("/")[3]
            since = params.get("since", [None])[0]
            room = self.ide.get_room(room_id)
            if room:
                diff = room.diff(since)
                self._send_json(diff.to_dict())
            else:
                self._send_json({"error": "room not found"}, 404)
        elif path.startswith("/ide/rooms/") and path.endswith("/task"):
            room_id = path.split("/")[3]
            status = self.ide.check(room_id)
            if status:
                self._send_json(status)
            else:
                self._send_json({"error": "no task for room"}, 404)
        elif path.startswith("/ide/rooms/") and "/files" in path:
            room_id = path.split("/")[3]
            room = self.ide.get_room(room_id)
            if room:
                self._send_json({"files": room.list_files()})
            else:
                self._send_json({"error": "room not found"}, 404)
        elif path.startswith("/ide/rooms/") and path.endswith("/status"):
            room_id = path.split("/")[3]
            room = self.ide.get_room(room_id)
            if room:
                self._send_json(room.to_dict())
            else:
                self._send_json({"error": "room not found"}, 404)
        elif path.startswith("/ide/tasks/"):
            task_id = path.split("/")[3]
            task = self.ide.get_task(task_id)
            if task:
                self._send_json(task.to_dict())
            else:
                self._send_json({"error": "task not found"}, 404)
        elif path == "/ide/status":
            self._send_json({
                "rooms": len(self.ide._rooms),
                "tasks": len(self.ide._tasks),
                "current_room": self.ide.current_room_id,
            })
        else:
            self._send_json({"error": "not found", "path": path}, 404)

    # ── POST routes ──────────────────────────────────────

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/ide/rooms":
            body = self._read_json()
            name = body.get("name", "unnamed")
            shell_type = body.get("shell_type", "seed-mini")
            room = self.ide.create_room(name, shell_type)
            self._send_json({"status": "created", "room": room.to_dict()}, 201)
        elif path.startswith("/ide/rooms/") and path.endswith("/prompt"):
            room_id = path.split("/")[3]
            body = self._read_json()
            text = body.get("prompt", "")
            context = body.get("context")
            room = self.ide.get_room(room_id)
            if room:
                response = room.execute(text, context)
                self._send_json({"response": response, "room_id": room_id})
            else:
                self._send_json({"error": "room not found"}, 404)
        elif path.startswith("/ide/rooms/") and path.endswith("/checkpoint"):
            room_id = path.split("/")[3]
            body = self._read_json()
            name = body.get("name")
            room = self.ide.get_room(room_id)
            if room:
                cp_name = room.checkpoint(name)
                self._send_json({"status": "checkpointed", "name": cp_name})
            else:
                self._send_json({"error": "room not found"}, 404)
        elif path.startswith("/ide/rooms/") and path.endswith("/dispatch"):
            room_id = path.split("/")[3]
            body = self._read_json()
            task_prompt = body.get("task", "")
            max_iter = body.get("max_iterations", 10)
            background = body.get("background", True)
            task = self.ide.dispatch(room_id, task_prompt, max_iter, background)
            if task:
                self._send_json({"status": "dispatched", "task_id": task.task_id, "room_id": room_id}, 201)
            else:
                self._send_json({"error": "room not found"}, 404)
        elif path.startswith("/ide/rooms/") and path.endswith("/write"):
            room_id = path.split("/")[3]
            body = self._read_json()
            filename = body.get("filename", "untitled.txt")
            content = body.get("content", "")
            room = self.ide.get_room(room_id)
            if room:
                room.write_file(filename, content)
                self._send_json({"status": "written", "filename": filename})
            else:
                self._send_json({"error": "room not found"}, 404)
        elif path.startswith("/ide/rooms/") and path.endswith("/shell"):
            room_id = path.split("/")[3]
            body = self._read_json()
            shell_type = body.get("shell_type", "seed-mini")
            room = self.ide.get_room(room_id)
            if room:
                room.shell.swap_shell(shell_type, **{k: v for k, v in body.items() if k != "shell_type"})
                self._send_json({"status": "swapped", "shell": room.shell.to_dict()})
            else:
                self._send_json({"error": "room not found"}, 404)
        else:
            self._send_json({"error": "not found", "path": path}, 404)

    # ── DELETE routes ────────────────────────────────────

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path.startswith("/ide/rooms/") and path.endswith("/task"):
            # Kill task for room
            room_id = path.split("/")[3]
            status = self.ide.check(room_id)
            if status:
                task_id = status["task_id"]
                killed = self.ide.kill_task(task_id)
                self._send_json({"status": "killed" if killed else "not found", "task_id": task_id})
            else:
                self._send_json({"error": "no task for room"}, 404)
        elif path.startswith("/ide/rooms/"):
            # Delete room
            room_id = path.split("/")[3]
            if self.ide.destroy_room(room_id):
                self._send_json({"status": "destroyed", "room_id": room_id})
            else:
                self._send_json({"error": "room not found"}, 404)
        elif path.startswith("/ide/tasks/"):
            task_id = path.split("/")[3]
            if self.ide.kill_task(task_id):
                self._send_json({"status": "killed", "task_id": task_id})
            else:
                self._send_json({"error": "task not found"}, 404)
        else:
            self._send_json({"error": "not found", "path": path}, 404)


# ---------------------------------------------------------------------------
# Standalone server
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="PLATO Agentic IDE Server")
    parser.add_argument("--port", type=int, default=8850, help="Port to listen on")
    args = parser.parse_args()

    SANDBOX_BASE.mkdir(parents=True, exist_ok=True)

    ide = RoomIDE()
    RoomIDEHandler.ide = ide

    server = HTTPServer(("127.0.0.1", args.port), RoomIDEHandler)

    print(f"{'='*60}")
    print(f"  PLATO Agentic IDE — Rooms as Live Agent Workspaces")
    print(f"  Listening on http://localhost:{args.port}")
    print(f"{'='*60}")
    print()
    print(f"  Endpoints:")
    print(f"    POST   /ide/rooms              — Create room")
    print(f"    GET    /ide/rooms              — List rooms")
    print(f"    POST   /ide/rooms/{{id}}/prompt  — Execute in room")
    print(f"    GET    /ide/rooms/{{id}}/scroll   — Scroll history")
    print(f"    GET    /ide/rooms/{{id}}/diff     — Diff changes")
    print(f"    POST   /ide/rooms/{{id}}/checkpoint — Save checkpoint")
    print(f"    POST   /ide/rooms/{{id}}/dispatch  — Send on task")
    print(f"    GET    /ide/rooms/{{id}}/task     — Check task status")
    print(f"    DELETE /ide/rooms/{{id}}/task     — Kill task")
    print(f"    DELETE /ide/rooms/{{id}}          — Destroy room")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n  IDE shutting down. Cleaning up sandboxes...")
        for room in ide._rooms.values():
            room.destroy()
        server.server_close()


if __name__ == "__main__":
    main()

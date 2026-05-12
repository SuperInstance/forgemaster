#!/usr/bin/env python3
"""
Lighthouse Runtime — Forgemaster's PLATO Agent Room System

The lighthouse doesn't sail the ships. It shows them where the rocks are.

Architecture:
  orient(task) → picks cheapest appropriate model, creates agent room
  relay(room, seeds) → seeds first, then agent runs
  gate(output) → credential leak, overclaim, external action checks

Filesystem layout per agent:
  state/agents/{room_id}/
    state.json      — agent status, model, task, timestamps
    tiles/          — PLATO tiles written by agent
    bottles/        — I2I bottles (outgoing fleet messages)
    log/            — execution logs
    seeds/          — seed discovery results (if applicable)
"""

import json
import os
import sys
import time
import uuid
import re
from pathlib import Path
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


# === Configuration ===

BASE_DIR = Path(__file__).parent
STATE_DIR = BASE_DIR / "state" / "agents"
PLATO_URL = os.environ.get("PLATO_URL", "http://147.224.38.131:8847")

# Cost per 1K queries (relative)
MODEL_COSTS = {
    "claude": 50.0,
    "glm": 5.0,
    "seed": 0.1,
    "deepseek": 0.2,
    "hermes": 0.15,
}

# Task → model mapping
TASK_MODEL_MAP = {
    "synthesis": ["claude"],
    "critique": ["claude"],
    "big_idea": ["claude"],
    "architecture": ["glm"],
    "complex_code": ["glm"],
    "orchestration": ["glm"],
    "discovery": ["seed"],
    "exploration": ["seed"],
    "variation": ["seed"],
    "drafting": ["seed", "deepseek"],
    "documentation": ["deepseek"],
    "research": ["deepseek"],
    "adversarial": ["hermes"],
    "second_opinion": ["hermes"],
}

# OpenClaw model mapping
OPENCLAW_MODELS = {
    "claude": "anthropic/claude-sonnet-4-20250514",
    "glm": "zai/glm-5.1",
    "seed": "deepinfra/ByteDance/Seed-2.0-mini",
    "deepseek": "deepseek/deepseek-chat",
    "hermes": "deepinfra/NousResearch/Hermes-3-Llama-3.1-70B",
}


class AgentStatus(str, Enum):
    ORIENTING = "orienting"
    SEEDING = "seeding"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETE = "complete"
    FAILED = "failed"


# === Room Management ===

def create_room(room_id: str, role: str, task: str, task_type: str, model: str) -> Path:
    """Create an agent room filesystem structure."""
    room_dir = STATE_DIR / room_id
    for subdir in ["tiles", "bottles", "log", "seeds"]:
        (room_dir / subdir).mkdir(parents=True, exist_ok=True)
    
    state = {
        "room_id": room_id,
        "role": role,
        "task": task,
        "task_type": task_type,
        "model": model,
        "openclaw_model": OPENCLAW_MODELS.get(model, model),
        "status": AgentStatus.ORIENTING.value,
        "generation": 0,
        "seed_iterations": 0,
        "crystallization_score": 0.0,
        "gated": False,
        "gate_passed": None,
        "created_at": int(time.time()),
        "updated_at": int(time.time()),
    }
    
    state_file = room_dir / "state.json"
    state_file.write_text(json.dumps(state, indent=2))
    
    return room_dir


def load_state(room_id: str) -> dict:
    """Load agent room state."""
    state_file = STATE_DIR / room_id / "state.json"
    if not state_file.exists():
        return {}
    return json.loads(state_file.read_text())


def save_state(room_id: str, state: dict):
    """Save agent room state."""
    state["updated_at"] = int(time.time())
    state_file = STATE_DIR / room_id / "state.json"
    state_file.write_text(json.dumps(state, indent=2))


# === Orient: Pick the right model for the task ===

def orient(task: str, task_type: str, role: str = "worker") -> dict:
    """
    Orient: pick the cheapest appropriate model and create an agent room.
    
    Returns the room state including model choice and OpenClaw model name.
    """
    # Find cheapest appropriate model
    models = TASK_MODEL_MAP.get(task_type, ["seed"])
    model = models[0]  # First choice is cheapest appropriate
    
    # Check capacity (simple: prefer cheaper models)
    # If first choice is claude/glm, check if we've used them recently
    room_id = f"agent-{model}-{role}-{uuid.uuid4().hex[:8]}"
    
    room_dir = create_room(room_id, role, task, task_type, model)
    
    state = load_state(room_id)
    
    log_entry(room_id, f"Oriented: task_type={task_type}, model={model}, room={room_id}")
    
    return {
        "room_id": room_id,
        "model": model,
        "openclaw_model": state["openclaw_model"],
        "task_type": task_type,
        "status": "orienting",
        "cost_estimate": MODEL_COSTS.get(model, 0.1),
    }


# === Relay: Seed first, then run ===

def relay(room_id: str, seed_iterations: int = 0) -> dict:
    """
    Relay: transition from orienting to running.
    Optionally run seed discovery first.
    """
    state = load_state(room_id)
    if not state:
        return {"error": f"Room {room_id} not found"}
    
    if seed_iterations > 0:
        state["status"] = AgentStatus.SEEDING.value
        state["seed_iterations"] = seed_iterations
        save_state(room_id, state)
        log_entry(room_id, f"Seeding: {seed_iterations} iterations")
        # In production, this would kick off seed discovery via Seed-2.0-mini
        # For now, mark as done
        state["status"] = AgentStatus.RUNNING.value
    else:
        state["status"] = AgentStatus.RUNNING.value
    
    save_state(room_id, state)
    log_entry(room_id, f"Relay: agent running, model={state['model']}")
    
    return {
        "room_id": room_id,
        "status": state["status"],
        "model": state["model"],
        "openclaw_model": state["openclaw_model"],
    }


# === Gate: Safety and alignment check ===

# Patterns that indicate potential issues
CREDENTIAL_PATTERNS = [
    r'(?:api[_-]?key|token|secret|password)\s*[=:]\s*["\']?[a-zA-Z0-9_-]{20,}',
    r'sk-[a-zA-Z0-9]{20,}',  # OpenAI keys
    r'ghp_[a-zA-Z0-9]{36}',  # GitHub PATs
    r'xox[bpas]-[a-zA-Z0-9-]+',  # Slack tokens
]

OVERCLAIM_PATTERNS = [
    r'I (?:can|will|am able to) (?:access|modify|delete|control) (?:your|the|all)',
    r'I have (?:full|unlimited|root|admin) (?:access|permissions|control)',
]

EXTERNAL_ACTION_PATTERNS = [
    r'(?:rm\s+-rf|sudo\s+rm|DROP\s+TABLE|DELETE\s+FROM\s+\*)',
]


def gate(room_id: str, output: str) -> dict:
    """
    Gate: check output for credential leaks, overclaims, and dangerous actions.
    """
    state = load_state(room_id)
    if not state:
        return {"error": f"Room {room_id} not found"}
    
    issues = []
    
    # Check for credential leaks
    for pattern in CREDENTIAL_PATTERNS:
        matches = re.findall(pattern, output, re.IGNORECASE)
        if matches:
            issues.append({
                "type": "credential_leak",
                "severity": "CRITICAL",
                "matches": len(matches),
                "action": "REJECT",
            })
    
    # Check for overclaims
    for pattern in OVERCLAIM_PATTERNS:
        matches = re.findall(pattern, output, re.IGNORECASE)
        if matches:
            issues.append({
                "type": "overclaim",
                "severity": "WARNING",
                "matches": len(matches),
                "action": "FLAG",
            })
    
    # Check for dangerous actions
    for pattern in EXTERNAL_ACTION_PATTERNS:
        matches = re.findall(pattern, output, re.IGNORECASE)
        if matches:
            issues.append({
                "type": "dangerous_action",
                "severity": "CRITICAL",
                "matches": len(matches),
                "action": "NEEDS_APPROVAL",
            })
    
    passed = all(i["action"] != "REJECT" for i in issues)
    needs_approval = any(i["action"] == "NEEDS_APPROVAL" for i in issues)
    
    state["gated"] = True
    state["gate_passed"] = passed and not needs_approval
    save_state(room_id, state)
    
    if passed and not needs_approval:
        state["status"] = AgentStatus.COMPLETE.value
    elif needs_approval:
        state["status"] = AgentStatus.PAUSED.value
    else:
        state["status"] = AgentStatus.FAILED.value
    
    save_state(room_id, state)
    log_entry(room_id, f"Gate: passed={passed}, needs_approval={needs_approval}, issues={len(issues)}")
    
    return {
        "room_id": room_id,
        "passed": passed,
        "needs_approval": needs_approval,
        "issues": issues,
        "status": state["status"],
    }


# === Tile Management ===

def write_tile(room_id: str, tile_type: str, content: str) -> dict:
    """Write a PLATO tile to an agent's room."""
    tiles_dir = STATE_DIR / room_id / "tiles"
    if not tiles_dir.exists():
        return {"error": f"Room {room_id} not found"}
    
    timestamp = int(time.time())
    tile_id = f"{tile_type}-{timestamp}"
    tile_file = tiles_dir / f"{tile_id}.json"
    
    tile = {
        "id": tile_id,
        "type": tile_type,
        "content": content,
        "room_id": room_id,
        "timestamp": timestamp,
    }
    
    tile_file.write_text(json.dumps(tile, indent=2))
    
    # Also submit to PLATO if available
    try:
        import urllib.request
        data = json.dumps({"room": room_id, "tile": tile}).encode()
        req = urllib.request.Request(
            f"{PLATO_URL}/room/{room_id}/tile",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass  # PLATO not available — tile is still local
    
    log_entry(room_id, f"Tile written: {tile_id}")
    return {"tile_id": tile_id, "room_id": room_id}


def write_bottle(room_id: str, target: str, message_type: str, content: str) -> dict:
    """Write an I2I bottle (inter-agent message)."""
    bottles_dir = STATE_DIR / room_id / "bottles"
    if not bottles_dir.exists():
        return {"error": f"Room {room_id} not found"}
    
    timestamp = int(time.time())
    date_str = time.strftime("%Y-%m-%d")
    bottle_id = f"{date_str}-{target}-{message_type}"
    bottle_file = bottles_dir / f"{bottle_id}.i2i"
    
    bottle_content = f"""[I2I:{message_type}] forgemaster → {target}

Room: {room_id}
Timestamp: {timestamp}

{content}

Status: PENDING
"""
    
    bottle_file.write_text(bottle_content)
    log_entry(room_id, f"Bottle written: {bottle_id} → {target}")
    return {"bottle_id": bottle_id, "room_id": room_id, "target": target}


# === Logging ===

def log_entry(room_id: str, message: str):
    """Append to agent room log."""
    log_dir = STATE_DIR / room_id / "log"
    if not log_dir.exists():
        return
    
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
    log_file = log_dir / "agent.log"
    with open(log_file, "a") as f:
        f.write(f"[{timestamp}] {message}\n")


# === Listing ===

def list_rooms(status_filter: Optional[str] = None) -> list:
    """List all agent rooms, optionally filtered by status."""
    rooms = []
    if not STATE_DIR.exists():
        return rooms
    
    for room_dir in sorted(STATE_DIR.iterdir()):
        if not room_dir.is_dir():
            continue
        state_file = room_dir / "state.json"
        if not state_file.exists():
            continue
        state = json.loads(state_file.read_text())
        if status_filter and state.get("status") != status_filter:
            continue
        rooms.append(state)
    
    return rooms


def resource_summary() -> dict:
    """Show resource usage across all rooms."""
    rooms = list_rooms()
    summary = {
        "total_rooms": len(rooms),
        "by_status": {},
        "by_model": {},
        "total_cost_estimate": 0.0,
    }
    
    for room in rooms:
        status = room.get("status", "unknown")
        model = room.get("model", "unknown")
        
        summary["by_status"][status] = summary["by_status"].get(status, 0) + 1
        summary["by_model"][model] = summary["by_model"].get(model, 0) + 1
        summary["total_cost_estimate"] += MODEL_COSTS.get(model, 0.1)
    
    return summary


# === CLI ===

def main():
    if len(sys.argv) < 2:
        print("Usage: lighthouse.py <command> [args...]")
        print("Commands:")
        print("  orient <task> <task_type> [role]        — Pick model, create room")
        print("  relay <room_id> [seed_iterations]        — Start agent running")
        print("  gate <room_id> <output_file>             — Safety check output")
        print("  gate-text <room_id> <text>               — Safety check text")
        print("  tile <room_id> <type> <content>          — Write PLATO tile")
        print("  bottle <room_id> <target> <type> <file>  — Write I2I bottle")
        print("  list [status]                            — List rooms")
        print("  state <room_id>                          — Show room state")
        print("  summary                                  — Resource summary")
        print("  log <room_id>                            — Show room log")
        print("  clean [status]                           — Remove rooms by status")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "orient":
        task = sys.argv[2] if len(sys.argv) > 2 else "unknown task"
        task_type = sys.argv[3] if len(sys.argv) > 3 else "drafting"
        role = sys.argv[4] if len(sys.argv) > 4 else "worker"
        result = orient(task, task_type, role)
        print(json.dumps(result, indent=2))
    
    elif cmd == "relay":
        room_id = sys.argv[2]
        seeds = int(sys.argv[3]) if len(sys.argv) > 3 else 0
        result = relay(room_id, seeds)
        print(json.dumps(result, indent=2))
    
    elif cmd == "gate":
        room_id = sys.argv[2]
        output_file = sys.argv[3]
        output = Path(output_file).read_text()
        result = gate(room_id, output)
        print(json.dumps(result, indent=2))
    
    elif cmd == "gate-text":
        room_id = sys.argv[2]
        text = " ".join(sys.argv[3:])
        result = gate(room_id, text)
        print(json.dumps(result, indent=2))
    
    elif cmd == "tile":
        room_id = sys.argv[2]
        tile_type = sys.argv[3]
        content = " ".join(sys.argv[4:])
        result = write_tile(room_id, tile_type, content)
        print(json.dumps(result, indent=2))
    
    elif cmd == "bottle":
        room_id = sys.argv[2]
        target = sys.argv[3]
        msg_type = sys.argv[4]
        content_file = sys.argv[5] if len(sys.argv) > 5 else None
        content = Path(content_file).read_text() if content_file else "Empty bottle"
        result = write_bottle(room_id, target, msg_type, content)
        print(json.dumps(result, indent=2))
    
    elif cmd == "list":
        status_filter = sys.argv[2] if len(sys.argv) > 2 else None
        rooms = list_rooms(status_filter)
        for room in rooms:
            print(f"  {room['room_id']}  status={room['status']}  model={room['model']}  task_type={room['task_type']}")
        if not rooms:
            print("  (no rooms)")
    
    elif cmd == "state":
        room_id = sys.argv[2]
        state = load_state(room_id)
        print(json.dumps(state, indent=2))
    
    elif cmd == "summary":
        s = resource_summary()
        print(json.dumps(s, indent=2))
    
    elif cmd == "log":
        room_id = sys.argv[2]
        log_file = STATE_DIR / room_id / "log" / "agent.log"
        if log_file.exists():
            print(log_file.read_text())
        else:
            print("  (no log)")
    
    elif cmd == "clean":
        status_filter = sys.argv[2] if len(sys.argv) > 2 else "complete"
        rooms = list_rooms(status_filter)
        removed = 0
        for room in rooms:
            import shutil
            room_dir = STATE_DIR / room["room_id"]
            shutil.rmtree(room_dir)
            removed += 1
        print(f"Cleaned {removed} rooms with status={status_filter}")
    
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()

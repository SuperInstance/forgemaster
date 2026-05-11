#!/usr/bin/env python3
"""
Fleet Service Guard v2 — Auto-Remediation Edition
Designed by Forgemaster ⚒️ for Oracle1 infrastructure

Monitors services, attempts restart, escalates via I2I on persistent failure.
"""

import socket
import subprocess
import time
import json
import os
from datetime import datetime, timezone
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────

SERVICES = {
    "keeper":         {"port": 8900, "restart": "systemctl --user restart keeper"},
    "agent-api":      {"port": 8901, "restart": "systemctl --user restart agent-api"},
    "holodeck":       {"port": 7778, "restart": "systemctl --user restart holodeck"},
    "seed-mcp":       {"port": 9438, "restart": "systemctl --user restart seed-mcp"},
    "fleet-dashboard":{"port": 4049, "restart": "systemctl --user restart fleet-dashboard"},
    "plato":          {"port": 8847, "restart": "systemctl --user restart plato"},
    "grammar-engine": {"port": 4045, "restart": "systemctl --user restart grammar-engine"},
    "arena":          {"port": 4044, "restart": "systemctl --user restart arena"},
    "grammar-compactor":{"port":4055, "restart": "systemctl --user restart grammar-compactor"},
    "matrix-bridge":  {"port": 6168, "restart": "systemctl --user restart matrix-bridge"},
    "crab-traps":     {"port": 4048, "restart": "systemctl --user restart crab-traps"},
}

RESTART_MAX_ATTEMPTS = 3
RESTART_WINDOW_SECONDS = 1800  # 30 minutes
ESCALATION_DIR = Path.home() / ".openclaw/workspace/for-fleet"
STATE_FILE = Path.home() / ".fleet-guard-state.json"
CHECK_INTERVAL = 300  # 5 minutes

# ── Live Port Check ────────────────────────────────────────────

def is_port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    """Socket probe — replaces stale cached state reads."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            result = s.connect_ex((host, port))
            return result == 0
    except (socket.error, OSError):
        return False

# ── Remediation ────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"restart_counts": {}, "escalated": {}}

def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))

def attempt_restart(name: str, cmd: str, state: dict) -> bool:
    """Try to restart a service. Returns True if restart was attempted."""
    now = time.time()
    counts = state["restart_counts"].setdefault(name, [])
    
    # Prune old attempts outside the window
    counts[:] = [t for t in counts if now - t < RESTART_WINDOW_SECONDS]
    
    if len(counts) >= RESTART_MAX_ATTEMPTS:
        return False  # Already maxed out
    
    try:
        subprocess.run(cmd, shell=True, timeout=30, capture_output=True)
        counts.append(now)
        state["restart_counts"][name] = counts
        save_state(state)
        return True
    except subprocess.TimeoutExpired:
        return False

def write_escalation_bottle(name: str, port: int, state: dict):
    """Write an I2I bottle when service can't be recovered."""
    now = datetime.now(timezone.utc)
    bottle_name = f"{now.strftime('%Y-%m-%d')}-fleet-guard-escalation-{name}.i2i"
    bottle_path = ESCALATION_DIR / bottle_name
    
    if bottle_path.exists():
        return  # Already escalated
    
    content = f"""[I2I:ESCALATION] Forgemaster Service Guard — {name} DOWN

Service: {name} (port {port})
Status: UNRECOVERABLE — {RESTART_MAX_ATTEMPTS} restart attempts failed
Detected: {now.isoformat()}
Action needed: Manual intervention required

Service guard attempted {RESTART_MAX_ATTEMPTS} restarts within {RESTART_WINDOW_SECONDS}s.
All attempts failed. The service is not self-healing.

Recommended:
- SSH to Oracle1 and check: systemctl --user status {name}
- Check logs: journalctl --user -u {name} --since '30 min ago'
- If config issue, fix and restart manually
- If resource issue (OOM, disk), address and restart

Auto-remediation exhausted. Human attention required.

Status: ESCALATED
"""
    bottle_path.write_text(content)
    state["escalated"][name] = now.isoformat()
    save_state(state)

# ── Main Loop ──────────────────────────────────────────────────

def check_all_services():
    state = load_state()
    results = {}
    
    for name, config in SERVICES.items():
        alive = is_port_open("localhost", config["port"])
        results[name] = alive
        
        if not alive:
            restarted = attempt_restart(name, config["restart"], state)
            if restarted:
                # Wait and recheck
                time.sleep(30)
                alive_after = is_port_open("localhost", config["port"])
                if alive_after:
                    results[name] = True  # Recovered
                elif len(state["restart_counts"].get(name, [])) >= RESTART_MAX_ATTEMPTS:
                    write_escalation_bottle(name, config["port"], state)
    
    return results

def main():
    """Single-check mode (call from cron every 5 min)."""
    results = check_all_services()
    
    down = [name for name, alive in results.items() if not alive]
    up_count = len(results) - len(down)
    
    timestamp = datetime.now(timezone.utc).isoformat()
    
    if down:
        print(f"[{timestamp}] {up_count}/{len(results)} UP — DOWN: {', '.join(down)}")
    else:
        print(f"[{timestamp}] {up_count}/{len(results)} UP — all services healthy")

if __name__ == "__main__":
    main()

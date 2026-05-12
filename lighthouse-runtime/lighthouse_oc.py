#!/bin/bin/env python3
"""
Lighthouse OpenClaw Bridge — Wire orient/relay/gate into subagent spawning.

Usage:
  python3 lighthouse_oc.py spawn "Build a hex grid lookup table" architecture
  python3 lighthouse_oc.py gate-last <room_id>
  python3 lighthouse_oc.py status

This script:
1. Calls orient() to pick the right model
2. Generates the subagent task prompt
3. Outputs the openclaw subagent spawn command
4. On gate, checks the output for safety
"""

import json
import sys
import time
from pathlib import Path

# Import lighthouse core
sys.path.insert(0, str(Path(__file__).parent))
from lighthouse import orient, relay, gate, load_state, list_rooms, resource_summary


# Task type descriptions for prompt generation
TASK_DESCRIPTIONS = {
    "synthesis": "Synthesize information from multiple sources into a unified understanding. Think step-by-step and provide deep analysis.",
    "critique": "Critically review the work, find weak points, edge cases, and potential failures. Be thorough and adversarial.",
    "big_idea": "Step back and think about the big picture. What are the fundamental principles? What's the meta-pattern?",
    "architecture": "Design system architecture with clear interfaces, data flow, and error handling. Use Rust where performance matters.",
    "complex_code": "Write production-quality code with tests, error handling, and documentation. Follow Rust best practices.",
    "orchestration": "Coordinate multiple components or agents. Design communication protocols and state management.",
    "discovery": "Explore the parameter space. Run many variations cheaply. Report what works and what doesn't.",
    "exploration": "Survey the landscape. What exists? What's missing? What are the key papers/repos/techniques?",
    "drafting": "Write clear, concise text. Get the structure right, fill in details later if needed.",
    "variation": "Generate many variations of the same thing. Find the interesting edge cases.",
    "documentation": "Write clear documentation. Include examples, edge cases, and cross-references.",
    "research": "Research the topic thoroughly. Cite sources. Distinguish known from speculative.",
    "adversarial": "Try to break it. Find the failure modes. What assumptions are wrong?",
    "second_opinion": "Provide an independent verification. Don't just agree — look for what might be missed.",
}


def spawn(task: str, task_type: str, role: str = "worker", seed_iterations: int = 0):
    """Orient and prepare a subagent spawn."""
    # Orient
    room = orient(task, task_type, role)
    room_id = room["room_id"]
    
    # Relay
    relay_result = relay(room_id, seed_iterations)
    
    # Generate task prompt
    description = TASK_DESCRIPTIONS.get(task_type, "Complete the task effectively.")
    
    full_prompt = f"""# Task: {task}

## Context
- Room: {room_id}
- Model tier: {room['model']}
- Task type: {task_type}
- Role: {role}

## Instructions
{description}

## Deliverables
1. Complete the task described above
2. Write a summary of what you did
3. Note any blockers or decisions made

## Constraints
- Follow the lighthouse protocol: orient → relay → gate
- Log important decisions
- Write PLATO tiles for significant findings
"""

    # Output the spawn info
    result = {
        "action": "spawn",
        "room_id": room_id,
        "model": room["openclaw_model"],
        "model_tier": room["model"],
        "task": task,
        "task_type": task_type,
        "prompt": full_prompt,
        "cost_estimate": room["cost_estimate"],
        "status": relay_result["status"],
    }
    
    print(json.dumps(result, indent=2))
    return result


def status():
    """Show lighthouse status."""
    s = resource_summary()
    print(json.dumps(s, indent=2))
    
    # Show active rooms
    active = list_rooms("running")
    if active:
        print("\n### Active Rooms:")
        for room in active:
            elapsed = int(time.time()) - room.get("created_at", 0)
            print(f"  {room['room_id']}")
            print(f"    model: {room['model']}  task: {room['task_type']}")
            print(f"    elapsed: {elapsed}s  gated: {room.get('gated', False)}")


def main():
    if len(sys.argv) < 2:
        print("Usage: lighthouse_oc.py <command> [args...]")
        print("Commands:")
        print("  spawn <task> <task_type> [role] [seeds]  — Orient + relay a subagent")
        print("  status                                   — Show lighthouse status")
        print("  rooms [status]                           — List rooms")
        print("  gate-last <room_id>                      — Gate check last output")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "spawn":
        task = sys.argv[2]
        task_type = sys.argv[3] if len(sys.argv) > 3 else "drafting"
        role = sys.argv[4] if len(sys.argv) > 4 else "worker"
        seeds = int(sys.argv[5]) if len(sys.argv) > 5 else 0
        spawn(task, task_type, role, seeds)
    
    elif cmd == "status":
        status()
    
    elif cmd == "rooms":
        from lighthouse import list_rooms as lr
        status_filter = sys.argv[2] if len(sys.argv) > 2 else None
        rooms = lr(status_filter)
        for room in rooms:
            print(f"  {room['room_id']}  status={room['status']}  model={room['model']}")
        if not rooms:
            print("  (no rooms)")
    
    elif cmd == "gate-last":
        room_id = sys.argv[2]
        state = load_state(room_id)
        if not state:
            print(f"Room {room_id} not found")
            sys.exit(1)
        # Find last tile
        tiles_dir = Path(__file__).parent / "state" / "agents" / room_id / "tiles"
        tiles = sorted(tiles_dir.glob("*.json")) if tiles_dir.exists() else []
        if tiles:
            last_tile = json.loads(tiles[-1].read_text())
            result = gate(room_id, last_tile.get("content", ""))
            print(json.dumps(result, indent=2))
        else:
            print(f"No tiles found for room {room_id}")
    
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()

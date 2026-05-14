#!/usr/bin/env python3
"""
Experiment 7: Emergent Orchestration — No Framework
Give agents tasks with NO orchestration. See if they self-organize.

Simulate 3 agents picking from a shared task pool (PLATO room).
Each agent is a model call. No dependencies, no manager, no process.
"""

import requests, json, time, os, random

KEY = open(os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")).read().strip()
URL = "https://api.deepinfra.com/v1/openai/chat/completions"

def query(system, user, max_tokens=150):
    resp = requests.post(URL,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
        json={"model": "ByteDance/Seed-2.0-mini", 
              "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
              "max_tokens": max_tokens, "temperature": 0.3},
        timeout=60)
    return resp.json()["choices"][0]["message"]["content"]

# 6 tasks in a shared pool — no dependencies defined
tasks = [
    {"id": "T1", "text": "Compute the Eisenstein norm of (3,-1)", "answer": "7"},
    {"id": "T2", "text": "Which Weyl sector is E12(3,-1) in?", "answer": "sector based on angle"},
    {"id": "T3", "text": "What's the snap target for float(0.499, 0.866)?", "answer": "nearest E12 point"},
    {"id": "T4", "text": "How many bytes does a float64 weight use?", "answer": "8"},
    {"id": "T5", "text": "What compression ratio does int16 pairing give vs float64?", "answer": "2x"},
    {"id": "T6", "text": "Name one advantage of Eisenstein lattice over Cartesian for hex symmetry", "answer": "rotational closure"},
]

# 3 agents with different personas
agents = [
    {"name": "Agent-A", "system": "You are a math specialist. Pick tasks you're best at. Be concise."},
    {"name": "Agent-B", "system": "You are a systems engineer. Pick tasks about memory and compression. Be concise."},
    {"name": "Agent-C", "system": "You are a generalist. Pick whatever's left. Be concise."},
]

# Phase 1: Each agent sees ALL tasks and picks which to do
print("="*60)
print("EXPERIMENT 7: Emergent Orchestration (No Framework)")
print("="*60)
print("\nPhase 1: Agent Self-Selection\n")

claimed = {}  # task_id → agent_name
results = {}

for agent in agents:
    task_list = "\n".join(f"  [{t['id']}] {t['text']}" for t in tasks if t['id'] not in claimed)
    prompt = f"""Available tasks (others may be claimed):
{task_list}

Pick exactly ONE task to work on. Reply with ONLY the task ID and your answer, like: "T1: <answer>" """
    
    try:
        response = query(agent["system"], prompt)
        # Parse which task they picked
        picked_id = None
        for t in tasks:
            if t['id'] in response[:5] and t['id'] not in claimed:
                picked_id = t['id']
                break
        
        if picked_id:
            claimed[picked_id] = agent["name"]
            results[picked_id] = {"agent": agent["name"], "response": response}
            print(f"  {agent['name']}: picked {picked_id} → {response[:80]}")
        else:
            print(f"  {agent['name']}: AMBIGUOUS PICK → {response[:80]}")
    except Exception as e:
        print(f"  {agent['name']}: ERROR → {e}")

# Phase 2: Remaining tasks — agents pick again
remaining = [t for t in tasks if t['id'] not in claimed]
if remaining:
    print(f"\nPhase 2: {len(remaining)} tasks unclaimed, re-offering\n")
    for agent in agents:
        task_list = "\n".join(f"  [{t['id']}] {t['text']}" for t in remaining)
        prompt = f"These tasks are still available:\n{task_list}\n\nPick ONE. Reply: 'T#: <answer>'"
        try:
            response = query(agent["system"], prompt)
            picked_id = None
            for t in remaining:
                if t['id'] in response[:5]:
                    picked_id = t['id']
                    break
            if picked_id and picked_id not in claimed:
                claimed[picked_id] = agent["name"]
                results[picked_id] = {"agent": agent["name"], "response": response}
                remaining = [t for t in remaining if t['id'] != picked_id]
                print(f"  {agent['name']}: picked {picked_id} → {response[:80]}")
        except Exception as e:
            print(f"  {agent['name']}: ERROR → {e}")

# Analysis
print(f"\n{'='*60}")
print("RESULTS")
print(f"{'='*60}")
print(f"Tasks covered: {len(claimed)}/{len(tasks)}")
print(f"Uncovered: {[t['id'] for t in tasks if t['id'] not in claimed]}")

# Check for self-organization patterns
agent_task_count = {}
for tid, aname in claimed.items():
    agent_task_count[aname] = agent_task_count.get(aname, 0) + 1

print(f"\nLoad distribution:")
for agent in agents:
    count = agent_task_count.get(agent['name'], 0)
    print(f"  {agent['name']}: {count} tasks")

# Did agents avoid duplicates?
print(f"\nDuplicate work: {'NONE' if len(claimed) == len(set(claimed.values())) else 'YES'}")

# Did specialization emerge?
print(f"\nSpecialization:")
for tid, aname in claimed.items():
    task = next(t for t in tasks if t['id'] == tid)
    print(f"  {tid}: {aname} → '{task['text'][:50]}...'")

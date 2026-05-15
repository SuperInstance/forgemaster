"""
lib/task_runner.py — Run PLATO room tasks with invisible routing.

A task runner reads a room's task queue, routes each task to the right
model, executes it, and writes the result back as a tile.

This is the loop inside the loop room. The room defines WHAT to do.
The task runner defines HOW (which model, what cost, how to validate).
"""

import json, urllib.request, urllib.parse, os, time, re, hashlib
from typing import Optional, List, Dict, Any


PLATO = os.environ.get("PLATO_URL", "http://localhost:8847")

# ─── Router (inline, zero deps) ──────────────────────────────────────────────

ROUTING = {
    "arithmetic":  {"model": "ByteDance/Seed-2.0-mini", "provider": "deepinfra", "temperature": 0.0, "cost": 0.05},
    "analysis":    {"model": "ByteDance/Seed-2.0-mini", "provider": "deepinfra", "temperature": 0.0, "cost": 0.05},
    "strategy":    {"model": "ByteDance/Seed-2.0-mini", "provider": "deepinfra", "temperature": 0.7, "cost": 0.05},
    "reasoning":   {"model": "google/gemini-3.1-flash-lite", "provider": "deepinfra", "temperature": 0.0, "cost": 0.002},
    "code":        {"model": "glm-5-turbo", "provider": "zai", "temperature": 0.3, "cost": 0.30},
    "conversation":{"model": "glm-5-turbo", "provider": "zai", "temperature": 0.5, "cost": 0.30},
}

def _detect_domain(prompt: str) -> str:
    p = prompt.lower()
    if any(s in p for s in ["compute","calculate","what is ","solve","sum","norm","move","score"]):
        if re.search(r'\d+\s*[+\-×*÷/]\s*\d+', p): return "arithmetic"
    if any(s in p for s in ["function","class ","def ","implement","refactor","write code"]): return "code"
    if any(s in p for s in ["why does","explain why","prove","is it true","therefore"]): return "reasoning"
    if any(s in p for s in ["design","architect","plan","strategy","propose"]): return "strategy"
    if any(s in p for s in ["analyze","compare","evaluate","diagnose"]): return "analysis"
    return "arithmetic"


def _get_creds(provider: str) -> tuple:
    """Returns (endpoint, api_key)."""
    cred_dir = os.path.expanduser("~/.openclaw/workspace/.credentials")
    if provider == "deepinfra":
        kf = os.path.join(cred_dir, "deepinfra-api-key.txt")
        key = open(kf).read().strip() if os.path.exists(kf) else ""
        return "https://api.deepinfra.com/v1/openai/chat/completions", key
    if provider == "zai":
        return ("https://api.z.ai/api/coding/paas/v4/chat/completions",
                os.environ.get("ZAI_KEY", "703f56774c324a76b8a283ce50b15744.tLKi6d9yeYza5Spg"))
    if provider == "groq":
        kf = os.path.join(cred_dir, "groq-api-key.txt")
        key = open(kf).read().strip() if os.path.exists(kf) else ""
        return "https://api.groq.com/openai/v1/chat/completions", key
    return "", ""


def _query_model(prompt: str, domain: str = None, system: str = None,
                 max_tokens: int = 100) -> dict:
    """Query model and return {answer, model, domain, cost, latency_ms}."""
    if domain is None:
        domain = _detect_domain(prompt)
    route = ROUTING.get(domain, ROUTING["arithmetic"])
    endpoint, api_key = _get_creds(route["provider"])

    if not api_key:
        return {"answer": "[no API key]", "error": True}

    sys_msg = system or "Give a direct, helpful answer."
    body = json.dumps({
        "model": route["model"],
        "messages": [
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": prompt},
        ],
        "temperature": route["temperature"],
        "max_tokens": max_tokens,
    }).encode()

    t0 = time.time()
    try:
        req = urllib.request.Request(endpoint, data=body, headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read())
        choice = data["choices"][0]["message"]
        text = choice.get("content", "") or choice.get("reasoning_content", "")
        return {
            "answer": text.strip(),
            "model": route["model"],
            "domain": domain,
            "temperature": route["temperature"],
            "cost_per_1k": route["cost"],
            "latency_ms": round((time.time() - t0) * 1000),
        }
    except Exception as e:
        return {"answer": f"[error: {e}]", "error": True, "domain": domain}


def _plato_post(tile: dict):
    """Submit tile to PLATO."""
    try:
        data = json.dumps(tile).encode()
        req = urllib.request.Request(f"{PLATO}/submit", data=data,
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5)
    except:
        pass


def _plato_get(path: str):
    """GET from PLATO."""
    try:
        resp = urllib.request.urlopen(f"{PLATO}/{path}", timeout=5)
        return json.loads(resp.read())
    except:
        return None


# ─── Task Types ───────────────────────────────────────────────────────────────

class Task:
    """A single task to execute."""
    def __init__(self, room_id: str, task_type: str, prompt: str,
                 system: str = None, max_tokens: int = 100,
                 validator: callable = None, domain: str = None):
        self.room_id = room_id
        self.task_type = task_type
        self.prompt = prompt
        self.system = system
        self.max_tokens = max_tokens
        self.validator = validator
        self.domain = domain

    def execute(self) -> dict:
        result = _query_model(self.prompt, self.domain, self.system, self.max_tokens)
        result["task_type"] = self.task_type
        result["room_id"] = self.room_id

        # Validate if provided
        if self.validator:
            result["valid"] = self.validator(result.get("answer", ""))

        # Write tile
        _plato_post({
            "room_id": self.room_id,
            "domain": self.domain or result.get("domain", "auto"),
            "agent": f"task-runner/{result.get('model', 'unknown')}",
            "question": f"task/{self.task_type}/{self.prompt[:80]}",
            "answer": result.get("answer", "")[:500],
            "tile_type": "task_result",
            "tags": ["task", self.task_type],
            "confidence": 0.9,
            "routing_meta": json.dumps({k: v for k, v in result.items()
                                        if k != "answer"}),
        })
        return result


class TaskPipeline:
    """Run a sequence of tasks, passing output forward."""
    def __init__(self, room_id: str):
        self.room_id = room_id
        self.results = []

    def add(self, task_type: str, prompt_fn: callable, **kwargs):
        """Add a task. prompt_fn receives previous results."""
        self.results.append({"type": task_type, "prompt_fn": prompt_fn, "kwargs": kwargs})
        return self

    def run(self) -> list:
        outputs = []
        for step in self.results:
            prompt = step["prompt_fn"](outputs)
            task = Task(self.room_id, step["type"], prompt, **step["kwargs"])
            result = task.execute()
            outputs.append(result)
        return outputs


# ─── Pre-built Task Factories ─────────────────────────────────────────────────

def summarize_tiles(room_id: str, n: int = 20) -> dict:
    """Summarize recent activity in a room."""
    data = _plato_get(f"room/{urllib.parse.quote(room_id, safe='')}/history")
    if not data:
        return {"answer": "no tiles found", "room_id": room_id}

    tiles = data.get("tiles", data) if isinstance(data, dict) else data
    recent = tiles[-n:]
    context = "\n".join(
        f"[{t.get('agent','?')}] {t.get('answer','')[:100]}"
        for t in recent
    )

    task = Task(room_id, "summarize",
                f"Summarize the recent activity in room '{room_id}':\n{context}",
                domain="analysis", max_tokens=200)
    return task.execute()


def analyze_errors(room_id: str) -> dict:
    """Find and explain errors in a room."""
    data = _plato_get(f"room/{urllib.parse.quote(room_id, safe='')}/history")
    if not data:
        return {"answer": "no tiles found"}

    tiles = data.get("tiles", data) if isinstance(data, dict) else data
    errors = [t for t in tiles if "ERROR" in str(t.get("answer", "")) or
              "error" in str(t.get("answer", "")).lower()]

    if not errors:
        return {"answer": "no errors found", "room_id": room_id}

    context = "\n".join(
        f"[{t.get('agent','?')}] {t.get('question','')[:60]}: {t.get('answer','')[:80]}"
        for t in errors[-10:]
    )

    task = Task(room_id, "error_analysis",
                f"Analyze these errors from room '{room_id}' and suggest fixes:\n{context}",
                domain="analysis", max_tokens=300)
    return task.execute()


def generate_code(room_id: str, spec: str) -> dict:
    """Generate code from a specification."""
    task = Task(room_id, "code_gen",
                f"Write code for: {spec}",
                domain="code", max_tokens=500)
    return task.execute()


def decompose_task(room_id: str, task_desc: str) -> list:
    """Decompose a task into sub-tasks, route each appropriately."""
    # Step 1: Analyze what needs to happen
    plan_result = _query_model(
        f"Decompose this task into 3-5 concrete sub-tasks. Give ONLY a numbered list:\n{task_desc}",
        domain="strategy", max_tokens=200,
    )

    plan_text = plan_result.get("answer", "")
    steps = [line.strip() for line in plan_text.split("\n")
             if line.strip() and line.strip()[0].isdigit()]

    # Step 2: Execute each step
    results = []
    for step in steps:
        domain = _detect_domain(step)
        result = _query_model(step, domain=domain, max_tokens=200)
        result["step"] = step[:80]
        result["domain"] = domain
        results.append(result)

        # Tile each step
        _plato_post({
            "room_id": room_id,
            "domain": domain,
            "agent": f"decomposer/{result.get('model','?')}",
            "question": f"decompose/{step[:80]}",
            "answer": result.get("answer", "")[:500],
            "tile_type": "decomposed_step",
            "tags": ["decompose", domain],
            "confidence": 0.8,
        })

    return results


# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: task_runner.py <command> [args]")
        print("  summarize <room_id>          — summarize room activity")
        print("  errors <room_id>             — analyze errors in room")
        print("  code <room_id> <spec>        — generate code")
        print("  decompose <room_id> <task>   — decompose and execute")
        print("  run <room_id> <prompt>       — single routed completion")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "summarize" and len(sys.argv) > 2:
        r = summarize_tiles(sys.argv[2])
        print(r.get("answer", ""))
    elif cmd == "errors" and len(sys.argv) > 2:
        r = analyze_errors(sys.argv[2])
        print(r.get("answer", ""))
    elif cmd == "code" and len(sys.argv) > 3:
        r = generate_code(sys.argv[2], " ".join(sys.argv[3:]))
        print(r.get("answer", ""))
    elif cmd == "decompose" and len(sys.argv) > 3:
        results = decompose_task(sys.argv[2], " ".join(sys.argv[3:]))
        for r in results:
            print(f"[{r.get('domain','?')}] {r.get('step','?')[:50]}")
            print(f"  {r.get('answer','')[:100]}")
    elif cmd == "run" and len(sys.argv) > 3:
        r = _query_model(" ".join(sys.argv[3:]))
        print(r.get("answer", ""))
        print(f"\n─── {r.get('model','?')} | {r.get('domain','?')} | "
              f"{r.get('latency_ms',0)}ms ───", file=sys.stderr)

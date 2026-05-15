"""
lib/router.py — Invisible fleet routing for PLATO rooms.

Every room that needs a model gets the cheapest one that won't break.
The 6,000+ trials are compressed into a lookup table.
Nobody thinks about critical angles. They just call room.complete().

This is TCP for model routing — it just works.
"""

import json, os, time, re
from typing import Optional, Tuple
from urllib import request, error as urllib_error


# ─── Routing Table (compressed from 6,000+ trials) ───────────────────────────
# Format: (model_id, provider, temperature, cost_per_1k_tokens)
# Order matters — first match wins for each domain.

DOMAIN_ROUTING = {
    # Primary: verified >90% accuracy
    "arithmetic": {"model": "ByteDance/Seed-2.0-mini", "provider": "deepinfra", "temperature": 0.0, "cost_per_1k": 0.05, "savings_vs_gpt4": "99.9%"},
    "analysis":   {"model": "ByteDance/Seed-2.0-mini", "provider": "deepinfra", "temperature": 0.0, "cost_per_1k": 0.05, "savings_vs_gpt4": "99%"},
    "strategy":   {"model": "ByteDance/Seed-2.0-mini", "provider": "deepinfra", "temperature": 0.7, "cost_per_1k": 0.05, "savings_vs_gpt4": "99%"},
    "reasoning":  {"model": "google/gemini-3.1-flash-lite", "provider": "deepinfra", "temperature": 0.0, "cost_per_1k": 0.002, "savings_vs_gpt4": "99.9%"},
    "code":       {"model": "glm-5-turbo", "provider": "zai", "temperature": 0.3, "cost_per_1k": 0.30, "savings_vs_gpt4": "84%"},
    "conversation":{"model": "glm-5-turbo", "provider": "zai", "temperature": 0.5, "cost_per_1k": 0.30, "savings_vs_gpt4": "84%"},
}
# Alternatives: verified 80%+
ROUTING_ALTERNATIVES = {
    "arithmetic": [
        {"model": "XiaomiMiMo/MiMo-V2.5", "provider": "deepinfra", "cost_per_1k": 0.05, "savings_vs_gpt4": "99.9%"},
        {"model": "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8", "provider": "deepinfra", "cost_per_1k": 0.10, "savings_vs_gpt4": "99%"},
        {"model": "llama-3.1-8b-instant", "provider": "groq", "cost_per_1k": 0.005, "savings_vs_gpt4": "99.9%"},
    ],
}

# Default fallback (seed-mini — never breaks on structured tasks)

# ─── Fast Path (Groq, ~50ms) ──────────────────────────────────────────────

def query_fast(prompt: str, max_tokens: int = 50) -> Tuple[str, dict]:
    """Query Groq for sub-100ms responses. Falls back to normal routing."""
    import urllib.request as ur
    
    key_path = os.path.expanduser("~/.openclaw/workspace/.credentials/groq-api-key.txt")
    if not os.path.exists(key_path):
        return query(prompt)  # fallback
    
    with open(key_path) as f:
        api_key = f.read().strip()
    
    domain = detect_domain(prompt)
    # Only use Groq for domains where it's calibrated >=80%
    groq_models = {
        "arithmetic": "llama-3.1-8b-instant",
        "code": "llama-3.3-70b-versatile", 
    }
    model = groq_models.get(domain)
    if not model:
        return query(prompt)  # not a Groq-calibrated domain
    
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": "Give ONLY the final answer."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "max_tokens": max_tokens,
    }).encode()
    
    t0 = time.time()
    try:
        req = ur.Request("https://api.groq.com/openai/v1/chat/completions",
            data=body, headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            })
        resp = ur.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        latency_ms = (time.time() - t0) * 1000
        choice = data["choices"][0]["message"]
        text = choice.get("content", "")
        return text.strip(), {
            "model": model, "domain": domain, "temperature": 0.0,
            "cost_per_1k": 0.005 if "8b" in model else 0.01,
            "latency_ms": round(latency_ms), "savings_vs_gpt4": "99.9%",
            "fast_path": True,
        }
    except:
        return query(prompt)  # fallback

DEFAULT_ROUTE = DOMAIN_ROUTING["arithmetic"]


# ─── Domain Detection (prompt → domain) ──────────────────────────────────────

def detect_domain(prompt: str) -> str:
    """Classify prompt into routing domain. Zero API calls."""
    p = prompt.lower()

    # Arithmetic signals
    if any(s in p for s in ["compute", "calculate", "what is ", "solve",
                             "sum", "multiply", "norm", "encode", "decode",
                             "move", "score", "count"]):
        # Check if it's pure numbers
        if re.search(r'\d+\s*[+\-×*÷/]\s*\d+', p):
            return "arithmetic"

    # Code signals
    if any(s in p for s in ["function", "class ", "def ", "import ",
                             "implement", "refactor", "fix bug",
                             "write code", "generate code"]):
        return "code"

    # Reasoning signals
    if any(s in p for s in ["why does", "explain why", "prove",
                             "is it true", "valid or invalid",
                             "therefore", "contradiction"]):
        return "reasoning"

    # Strategy/design signals
    if any(s in p for s in ["design", "architect", "plan", "strategy",
                             "propose", "brainstorm", "create",
                             "what should", "how would you"]):
        return "strategy"

    # Analysis signals
    if any(s in p for s in ["analyze", "compare", "evaluate", "assess",
                             "detect", "find patterns", "classify",
                             "diagnose"]):
        return "analysis"

    # Conversation signals
    if any(s in p for s in ["hello", "tell me about", "describe",
                             "narrate", "roleplay", "as an npc"]):
        return "conversation"

    return "arithmetic"  # safe default


# ─── Model Query ──────────────────────────────────────────────────────────────

def _get_api_key(provider: str) -> str:
    """Load API key for provider."""
    cred_dir = os.path.expanduser("~/.openclaw/workspace/.credentials")
    key_files = {
        "deepinfra": "deepinfra-api-key.txt",
        "groq": "groq-api-key.txt",
        "zai": None,  # hardcoded for now
    }

    if provider == "zai":
        return "703f56774c324a76b8a283ce50b15744.tLKi6d9yeYza5Spg"

    fname = key_files.get(provider)
    if fname:
        path = os.path.join(cred_dir, fname)
        if os.path.exists(path):
            with open(path) as f:
                return f.read().strip()
    return ""


def _get_endpoint(provider: str) -> str:
    endpoints = {
        "deepinfra": "https://api.deepinfra.com/v1/openai/chat/completions",
        "zai": "https://api.z.ai/api/coding/paas/v4/chat/completions",
        "groq": "https://api.groq.com/openai/v1/chat/completions",
    }
    return endpoints.get(provider, "")


def query(prompt: str, domain: str = None, max_tokens: int = 100,
          system: str = None) -> Tuple[str, dict]:
    """
    Query the cheapest safe model for the given prompt.

    Returns (answer_text, metadata).
    Metadata includes: model, domain, cost, latency_ms.
    """
    if domain is None:
        domain = detect_domain(prompt)

    route = DOMAIN_ROUTING.get(domain, DEFAULT_ROUTE)
    api_key = _get_api_key(route["provider"])
    endpoint = _get_endpoint(route["provider"])

    if not api_key or not endpoint:
        return "ERROR: no API key for provider", {"error": True}

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
        req = request.Request(endpoint, data=body, headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })
        resp = request.urlopen(req, timeout=30)
        data = json.loads(resp.read())
        latency_ms = (time.time() - t0) * 1000

        choice = data["choices"][0]["message"]
        content = choice.get("content", "")
        reasoning = choice.get("reasoning_content", "")
        text = content if content.strip() else reasoning

        meta = {
            "model": route["model"],
            "domain": domain,
            "temperature": route["temperature"],
            "cost_per_1k": route["cost_per_1k"],
            "latency_ms": round(latency_ms),
            "savings_vs_gpt4": route["savings_vs_gpt4"],
        }
        return text, meta

    except Exception as e:
        return f"ERROR: {e}", {"error": True, "domain": domain}


# ─── Room Integration ─────────────────────────────────────────────────────────

def room_complete(room_id: str, prompt: str, plato_url: str = None) -> dict:
    """
    The one function rooms call. Gets the answer, records it as a tile.

    Usage in rooms:
        from router import room_complete
        result = room_complete("my-room", "compute the norm of 3+2ω")
        # result = {"answer": "...", "model": "seed-mini", "cost": "$0.01"}

    Nobody thinks about which model. Nobody thinks about temperature.
    They just complete the room task.
    """
    answer, meta = query(prompt)

    # Submit to PLATO as a tile
    if plato_url is None:
        plato_url = os.environ.get("PLATO_URL", "http://localhost:8847")

    tile = {
        "room_id": room_id,
        "domain": meta.get("domain", "auto"),
        "agent": f"router/{meta.get('model', 'unknown')}",
        "question": prompt[:200],
        "answer": answer[:500],
        "tile_type": "routed_completion",
        "routing_meta": json.dumps(meta),
    }

    try:
        data = json.dumps(tile).encode()
        req = request.Request(
            f"{plato_url}/submit",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        request.urlopen(req, timeout=5)
    except:
        pass  # PLATO down — still return the answer

    return {"answer": answer, **meta}


# ─── CLI Interface ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: router.py <prompt> [domain]")
        print("Domains:", ", ".join(DOMAIN_ROUTING.keys()))
        sys.exit(1)

    prompt = sys.argv[1]
    domain = sys.argv[2] if len(sys.argv) > 2 else None

    answer, meta = query(prompt, domain)
    print(answer)
    if meta.get("model"):
        print(f"\n--- {meta['model']} | {meta.get('domain','?')} | "
              f"{meta.get('latency_ms',0):.0f}ms | ${meta.get('cost_per_1k',0)}/1K | "
              f"saves {meta.get('savings_vs_gpt4','?')} vs GPT-4 ---",
              file=sys.stderr)

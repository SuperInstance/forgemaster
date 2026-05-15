"""
lib/officer.py — A PLATO officer that walks into rooms and works.

An officer is an OpenClaw agent wrapped in PLATO protocol.
It reads rooms, understands them, maintains them, controls them.

What makes an officer different from a loop:
  - It uses the fleet router to pick models per-task
  - It emits tiles with provenance (which model, which domain, what cost)
  - It detects when a room needs attention and escalates
  - It can maintain multiple rooms simultaneously
"""

import json, urllib.request, urllib.parse, os, sys, threading, time, re

PLATO = os.environ.get("PLATO_URL", "http://localhost:8847")

officers = {}

# ─── Router Integration ──────────────────────────────────────────────────────

def _detect_domain(prompt):
    """Classify prompt into routing domain."""
    p = prompt.lower()
    if any(s in p for s in ["compute","calculate","what is ","solve","sum","norm","move","score"]):
        if re.search(r'\d+\s*[+\-×*÷/]\s*\d+', p): return "arithmetic"
    if any(s in p for s in ["function","class ","def ","implement","refactor","fix bug"]): return "code"
    if any(s in p for s in ["why does","explain why","prove","is it true","therefore"]): return "reasoning"
    if any(s in p for s in ["design","architect","plan","strategy","propose"]): return "strategy"
    if any(s in p for s in ["analyze","compare","evaluate","diagnose"]): return "analysis"
    return "arithmetic"

ROUTING = {
    "arithmetic": {"model": "ByteDance/Seed-2.0-mini", "provider": "deepinfra", "temperature": 0.0, "cost": 0.05},
    "analysis":   {"model": "ByteDance/Seed-2.0-mini", "provider": "deepinfra", "temperature": 0.0, "cost": 0.05},
    "strategy":   {"model": "ByteDance/Seed-2.0-mini", "provider": "deepinfra", "temperature": 0.7, "cost": 0.05},
    "reasoning":  {"model": "google/gemini-3.1-flash-lite", "provider": "deepinfra", "temperature": 0.0, "cost": 0.002},
    "code":       {"model": "glm-5-turbo", "provider": "zai", "temperature": 0.3, "cost": 0.30},
    "conversation":{"model": "glm-5-turbo", "provider": "zai", "temperature": 0.5, "cost": 0.30},
}

def _get_key(provider):
    cred_dir = os.path.expanduser("~/.openclaw/workspace/.credentials")
    if provider == "deepinfra":
        p = os.path.join(cred_dir, "deepinfra-api-key.txt")
        return open(p).read().strip() if os.path.exists(p) else ""
    if provider == "zai":
        return os.environ.get("ZAI_KEY", "703f56774c324a76b8a283ce50b15744.tLKi6d9yeYza5Spg")
    if provider == "groq":
        p = os.path.join(cred_dir, "groq-api-key.txt")
        return open(p).read().strip() if os.path.exists(p) else ""
    return ""

def _get_endpoint(provider):
    return {
        "deepinfra": "https://api.deepinfra.com/v1/openai/chat/completions",
        "zai": "https://api.z.ai/api/coding/paas/v4/chat/completions",
        "groq": "https://api.groq.com/openai/v1/chat/completions",
    }.get(provider, "")


def route_and_query(prompt, system="Give a direct, helpful answer.", max_tokens=150):
    """Route to cheapest safe model and return (answer, metadata)."""
    domain = _detect_domain(prompt)
    route = ROUTING.get(domain, ROUTING["arithmetic"])
    api_key = _get_key(route["provider"])
    endpoint = _get_endpoint(route["provider"])

    if not api_key:
        return "[no API key]", {"domain": domain, "error": True}

    body = json.dumps({
        "model": route["model"],
        "messages": [
            {"role": "system", "content": system},
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
        return text.strip(), {
            "domain": domain,
            "model": route["model"],
            "temperature": route["temperature"],
            "cost": route["cost"],
            "latency_ms": round((time.time() - t0) * 1000),
        }
    except Exception as e:
        return f"[error: {e}]", {"domain": domain, "error": True}


# ─── Room Reading ─────────────────────────────────────────────────────────────

def read_room(room_id):
    """Read tiles from a room."""
    try:
        url = f"{PLATO}/room/{urllib.parse.quote(room_id, safe='')}/history"
        resp = urllib.request.urlopen(url, timeout=5)
        data = json.loads(resp.read())
        tiles = data.get("tiles", data) if isinstance(data, dict) else data
        return tiles
    except:
        return []


def write_tile(room_id, question, answer, domain="officer", extra=None):
    """Write a tile to a room."""
    tile = {
        "room_id": room_id,
        "domain": domain,
        "agent": f"officer/{os.environ.get('OFFICER_ID', 'unknown')}",
        "question": question[:200],
        "answer": answer[:500],
        "tile_type": "officer_work",
        "tags": ["officer"],
        "confidence": 0.9,
    }
    if extra:
        tile["routing_meta"] = json.dumps(extra)
    try:
        data = json.dumps(tile).encode()
        req = urllib.request.Request(f"{PLATO}/submit", data=data,
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5)
    except:
        pass


# ─── Officer Behaviors ────────────────────────────────────────────────────────

def summarize_room(room_id, officer_id):
    """Read recent tiles, summarize what's happening."""
    tiles = read_room(room_id)
    if not tiles:
        return None

    recent = tiles[-10:]
    context = "\n".join(
        f"[{t.get('agent','?')}] {t.get('question','')[:50]}: {t.get('answer','')[:80]}"
        for t in recent
    )
    prompt = f"Summarize the recent activity in room '{room_id}' in 2-3 sentences:\n\n{context}"
    answer, meta = route_and_query(prompt, system="Summarize concisely.")
    return answer, meta


def detect_anomalies(room_id):
    """Check for signs that a room needs attention."""
    tiles = read_room(room_id)
    if not tiles:
        return []

    anomalies = []
    for t in tiles[-20:]:
        answer = str(t.get("answer", ""))
        if "ERROR" in answer or "error" in answer.lower():
            anomalies.append({"type": "error", "tile": t.get("_hash","?"), "msg": answer[:100]})
        if "BLOCKED" in answer:
            anomalies.append({"type": "blocked", "tile": t.get("_hash","?")})
        confidence = t.get("confidence", 1.0)
        if isinstance(confidence, (int, float)) and confidence < 0.3:
            anomalies.append({"type": "low_confidence", "tile": t.get("_hash","?"), "value": confidence})

    return anomalies


# ─── Officer Loop ─────────────────────────────────────────────────────────────

def spawn_officer(name="officer", rooms_to_watch=None):
    """Spawn a new officer agent. Returns officer ID."""
    oid = f"{name}-{int(time.time())}"
    os.environ["OFFICER_ID"] = oid

    if rooms_to_watch is None:
        rooms_to_watch = []

    def officer_loop():
        print(f"🖖 Officer {oid} on duty")
        tick = 0
        while True:
            tick += 1
            try:
                # 1. Watch assigned rooms
                for room_id in rooms_to_watch:
                    # Summarize every 10 ticks
                    if tick % 10 == 0:
                        result = summarize_room(room_id, oid)
                        if result:
                            answer, meta = result
                            write_tile(room_id, f"officer/{oid}/summary-tick-{tick}",
                                      answer, domain="officer_summary", extra=meta)

                    # Detect anomalies every tick
                    anomalies = detect_anomalies(room_id)
                    for a in anomalies[:3]:
                        write_tile(room_id, f"officer/{oid}/anomaly-{a['type']}",
                                  json.dumps(a), domain="officer_alert")

                # 2. Heartbeat
                write_tile("officers", f"officer/{oid}/tick-{tick}",
                          json.dumps({"tick": tick, "rooms": rooms_to_watch}),
                          domain="officer_heartbeat")

            except Exception as e:
                pass

            time.sleep(30)

    t = threading.Thread(target=officer_loop, daemon=True)
    t.start()
    officers[oid] = {"thread": t, "rooms": rooms_to_watch, "name": name}

    # Register
    write_tile("officers", f"officer/{oid}/spawned",
              json.dumps({"oid": oid, "name": name, "rooms": rooms_to_watch, "status": "active"}),
              domain="officer_registry")

    return oid


def list_officers():
    return {oid: {"name": o["name"], "rooms": o["rooms"]} for oid, o in officers.items()}


def halt_officer(oid):
    if oid in officers:
        write_tile("officers", f"officer/{oid}/halted",
                  json.dumps({"oid": oid, "status": "halted"}),
                  domain="officer_registry")
        del officers[oid]
        return True
    return False


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: officer.py spawn <name> [room1,room2,...]")
        print("       officer.py list")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "spawn":
        name = sys.argv[2] if len(sys.argv) > 2 else "officer"
        rooms = sys.argv[3].split(",") if len(sys.argv) > 3 else []
        oid = spawn_officer(name, rooms)
        print(f"🖖 {oid} watching {rooms or 'no rooms'}")
        try:
            while True: time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n🖖 {oid} standing down")
    elif cmd == "list":
        for oid, info in list_officers().items():
            print(f"  {oid}: watching {info['rooms']}")

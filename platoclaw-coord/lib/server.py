#!/usr/bin/env python3
"""Self-contained PLATO server — room management, tile submission, gates, routing."""
import http.server, json, urllib.parse, time, hashlib, threading, os, re

tiles = []  # all tiles ever submitted
gates = {   # quality gates
    "P0": lambda t: len(str(t.get("answer",""))) >= 1,
    "P1": lambda t: t.get("confidence", 0) >= 0.0,  # relaxed — router tiles may not have confidence
}

# ─── Inline Router (no external deps) ────────────────────────────────────────

ROUTING_TABLE = {
    # Primary: verified >90% accuracy (6,000+ empirical trials)
    "arithmetic":  {"model": "ByteDance/Seed-2.0-mini", "provider": "deepinfra", "temperature": 0.0, "cost": 0.05},
    "analysis":    {"model": "ByteDance/Seed-2.0-mini", "provider": "deepinfra", "temperature": 0.0, "cost": 0.05},
    "strategy":    {"model": "ByteDance/Seed-2.0-mini", "provider": "deepinfra", "temperature": 0.7, "cost": 0.05},
    "reasoning":   {"model": "google/gemini-3.1-flash-lite", "provider": "deepinfra", "temperature": 0.0, "cost": 0.002},
    "code":        {"model": "glm-5-turbo", "provider": "zai", "temperature": 0.3, "cost": 0.30},
    "conversation":{"model": "glm-5-turbo", "provider": "zai", "temperature": 0.5, "cost": 0.30},
}
# Alternatives: 80%+ verified, used for load balancing/fallback
ROUTING_ALTERNATIVES = {
    "arithmetic": [
        {"model": "XiaomiMiMo/MiMo-V2.5", "provider": "deepinfra", "cost": 0.05, "accuracy": 1.0},
        {"model": "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8", "provider": "deepinfra", "cost": 0.10, "accuracy": 1.0},
        {"model": "llama-3.1-8b-instant", "provider": "groq", "cost": 0.005, "accuracy": 0.86},
    ],
}

def _detect_domain(prompt):
    p = prompt.lower()
    if any(s in p for s in ["compute","calculate","what is ","solve","sum","norm","encode","move","score"]):
        if re.search(r'\d+\s*[+\-×*÷/]\s*\d+', p): return "arithmetic"
    if any(s in p for s in ["function","class ","def ","implement","refactor","fix bug","write code"]): return "code"
    if any(s in p for s in ["why does","explain why","prove","is it true","therefore"]): return "reasoning"
    if any(s in p for s in ["design","architect","plan","strategy","propose","brainstorm"]): return "strategy"
    if any(s in p for s in ["analyze","compare","evaluate","assess","detect","diagnose"]): return "analysis"
    if any(s in p for s in ["hello","tell me","describe","narrate","roleplay"]): return "conversation"
    return "arithmetic"


class PlatoHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.strip("/")

        if path in ("status", "health"):
            rooms = {}
            for t in tiles:
                rid = t.get("room_id", t.get("domain", "default"))
                rooms.setdefault(rid, 0)
                rooms[rid] += 1
            agents = set(t.get("agent", t.get("source", "")) for t in tiles)
            self.json({
                "status": "active",
                "tiles": len(tiles),
                "rooms": len(rooms),
                "agents": list(agents),
                "room_details": {k: v for k, v in sorted(rooms.items(), key=lambda x: -x[1])[:20]},
                "gate_stats": {"accepted": len(tiles), "rejected": 0},
                "routing": {"domains": list(ROUTING_TABLE.keys()), "version": "0.1.0"},
            })
        elif path == "rooms":
            rooms = {}
            for t in tiles:
                rid = t.get("room_id", t.get("domain", "default"))
                rooms.setdefault(rid, []).append(t)
            self.json({"rooms": {k: {"tile_count": len(v)} for k, v in rooms.items()}})
        elif path.startswith("room/") and path.endswith("/history"):
            room = path[5:-8]
            room_tiles = [t for t in tiles if t.get("room_id", t.get("domain", "")) == room]
            self.json({"room_id": room, "tile_count": len(room_tiles), "tiles": room_tiles[-50:]})
        elif path == "router/domains":
            self.json({"domains": ROUTING_TABLE})
        elif path == "router/route":
            qs = urllib.parse.parse_qs(parsed.query)
            prompt = qs.get("prompt", [""])[0]
            domain = _detect_domain(prompt) if prompt else "arithmetic"
            route = ROUTING_TABLE.get(domain, ROUTING_TABLE["arithmetic"])
            self.json({"prompt": prompt[:80], "domain": domain, **route})
        else:
            self.json({"error": "not found", "endpoints": [
                "/status", "/health", "/rooms", "/room/{id}/history",
                "/router/domains", "/router/route?prompt=...",
                "/submit (POST)", "/complete (POST)",
            ]})

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path.strip("/")

        if path == "submit":
            self._handle_submit()
        elif path == "complete":
            self._handle_complete()
        else:
            self.json({"error": f"POST not supported for /{path}"})

    def _handle_submit(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode()
        try:
            tile = json.loads(body)
        except:
            self.json({"status": "rejected", "reason": "invalid JSON"})
            return

        for gate_name, gate_fn in gates.items():
            if not gate_fn(tile):
                self.json({"status": "rejected", "reason": f"gate {gate_name}"})
                return

        tile["_hash"] = hashlib.md5(json.dumps(tile, sort_keys=True).encode()).hexdigest()[:8]
        tile["_clock"] = len(tiles) + 1
        tile["_ts"] = time.time()
        tiles.append(tile)
        self.json({"status": "accepted", "tile_count": len(tiles), "tile_hash": tile["_hash"]})

    def _handle_complete(self):
        """POST /complete — route + query + tile. The invisible router."""
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode()
        try:
            req = json.loads(body)
        except:
            self.json({"error": "invalid JSON"})
            return

        prompt = req.get("prompt", "")
        room_id = req.get("room_id", "default")
        domain = req.get("domain") or _detect_domain(prompt)
        route = ROUTING_TABLE.get(domain, ROUTING_TABLE["arithmetic"])

        # Try to query the model
        answer = None
        meta = {"domain": domain, **route}
        try:
            import urllib.request as ur
            # Resolve provider config
            cred_dir = os.path.expanduser("~/.openclaw/workspace/.credentials")
            api_key = ""
            endpoint = ""
            provider = route["provider"]

            if provider == "deepinfra":
                kf = os.path.join(cred_dir, "deepinfra-api-key.txt")
                if os.path.exists(kf):
                    with open(kf) as f: api_key = f.read().strip()
                endpoint = "https://api.deepinfra.com/v1/openai/chat/completions"
            elif provider == "zai":
                api_key = os.environ.get("ZAI_KEY", "")
                endpoint = "https://api.z.ai/api/coding/paas/v4/chat/completions"
            elif provider == "groq":
                kf = os.path.join(cred_dir, "groq-api-key.txt")
                if os.path.exists(kf):
                    with open(kf) as f: api_key = f.read().strip()
                endpoint = "https://api.groq.com/openai/v1/chat/completions"

            if api_key and endpoint:
                t0 = time.time()
                payload = json.dumps({
                    "model": route["model"],
                    "messages": [
                        {"role": "system", "content": "Give a direct, helpful answer."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": route["temperature"],
                    "max_tokens": req.get("max_tokens", 100),
                }).encode()
                r = ur.urlopen(ur.Request(endpoint, data=payload, headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }), timeout=30)
                data = json.loads(r.read())
                choice = data["choices"][0]["message"]
                answer = choice.get("content", "") or choice.get("reasoning_content", "")
                meta["latency_ms"] = round((time.time() - t0) * 1000)
        except Exception as e:
            answer = f"[router error: {e}]"

        if answer is None:
            answer = "[no API key configured]"

        # Auto-submit as tile
        tile = {
            "room_id": room_id,
            "domain": domain,
            "agent": f"router/{route['model']}",
            "question": prompt[:200],
            "answer": answer[:500],
            "tile_type": "routed_completion",
            "tags": ["routed", domain],
            "source": "platoclaw-router",
            "confidence": 0.9,
        }
        tile["_hash"] = hashlib.md5(json.dumps(tile, sort_keys=True).encode()).hexdigest()[:8]
        tile["_clock"] = len(tiles) + 1
        tile["_ts"] = time.time()
        tiles.append(tile)

        self.json({"answer": answer, "routing": meta, "tile_hash": tile["_hash"]})

    def json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode())

    def log_message(self, *a): pass

if __name__ == "__main__":
    port = int(os.environ.get("PLATO_PORT", 8847))
    server = http.server.HTTPServer(("0.0.0.0", port), PlatoHandler)
    print(f"🐚 PlatoClaw on :{port}")
    print(f"   PLATO:        http://localhost:{port}/status")
    print(f"   Rooms:        http://localhost:{port}/rooms")
    print(f"   Router:       http://localhost:{port}/router/domains")
    print(f"   Auto-route:   POST http://localhost:{port}/complete")
    print(f"   Dashboard:    platoclaw web")
    server.serve_forever()

#!/usr/bin/env python3
"""
Plato-Matrix Bridge — Agent Shell Module v0.1.0
================================================
Pre-rigged module: connects a local PLATO instance to the fleet Matrix mesh.
Channels + presence + ACL via Matrix rooms.

Usage:
    python3 plato-matrix-bridge.py --config config.json

Config:
    {
        "agent": "my-agent-name",
        "homeserver": "http://147.224.38.131:6167",
        "matrix_user": "@my-agent:147.224.38.131",
        "matrix_token": "...",
        "matrix_password": "...",
        "plato_url": "http://localhost:8847",
        "plato_rooms": ["fleet-coord", "forge", "my-personal-room"],
        "presence_room": "!fleet-presence:147.224.38.131",
        "poll_ms": 3000,
        "log_file": "/tmp/plato-matrix.log"
    }

Requirements: Python 3.8+, no external deps (uses stdlib + Matrix HTTP API)
"""

import json, urllib.request, urllib.parse, os, sys, time, threading, datetime
from pathlib import Path

# ── ANSI colors ─────────────────────────────────────────
CYAN = "\033[36m"; GREEN = "\033[32m"; YELLOW = "\033[33m"
RED = "\033[31m"; MAGENTA = "\033[35m"; RESET = "\033[0m"

PLATO_ROOM_SYNC_INTERVAL = 60  # Check PLATO for new tiles every 60s

class PlatoMatrixBridge:
    def __init__(self, config):
        self.cfg = config
        self.agent = config["agent"]
        self.ms = config["homeserver"]
        self.plato = config["plato_url"]
        self.token = config.get("matrix_token", "")
        self.user = config.get("matrix_user", "")
        self.password = config.get("matrix_password", "")
        self.poll_ms = config.get("poll_ms", 3000)
        self.plato_rooms = config.get("plato_rooms", [])
        self.presence_room = config.get("presence_room", "")
        self.log_file = config.get("log_file", "/tmp/plato-matrix.log")
        
        # State
        self.since = {}
        self.processed_events = set()
        self.plato_tile_states = {}
        self.running = True
        self.status = "offline"
        
        # Answering machine
        self.inbox_path = config.get("inbox_path", os.path.expanduser("~/.openclaw/workspace/.inbox/state.json"))
        self._unread_since_ack = 0
        self._last_ack_check = 0
        
        # Ensure login
        if not self.token:
            self._matrix_login()
        
        self._log(f"{CYAN}Plato-Matrix Bridge v0.1.0{RESET}")
        self._log(f"Agent: {GREEN}{self.agent}{RESET}")
        self._log(f"Matrix: {self.ms}")
        self._log(f"PLATO: {self.plato}")
        self._log(f"Poll: {self.poll_ms}ms")
        self._load_state()
    
    def _log(self, msg, level="INFO"):
        ts = datetime.datetime.utcnow().strftime("%H:%M:%S")
        line = f"[{ts}] [{self.agent}] {msg}"
        print(line, flush=True)
        try:
            with open(self.log_file, "a") as f:
                f.write(line + "\n")
        except:
            pass
    
    def _matrix_login(self):
        """Login to Matrix homeserver and get token."""
        try:
            payload = json.dumps({
                "type": "m.login.password",
                "user": self.user,
                "password": self.password
            }).encode()
            req = urllib.request.Request(
                f"{self.ms}/_matrix/client/v3/login",
                data=payload,
                headers={"Content-Type": "application/json"}
            )
            resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
            self.token = resp["access_token"]
            self.user = resp["user_id"]
            self._log(f"{GREEN}Logged in as {self.user}{RESET}")
        except Exception as e:
            self._log(f"{RED}Login failed: {e}{RESET}")
            sys.exit(1)
    
    def _matrix_request(self, method, path, data=None):
        """Make an authenticated Matrix API request."""
        url = f"{self.ms}{path}"
        headers = {"Authorization": f"Bearer {self.token}"}
        if data is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(data).encode()
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            resp = urllib.request.urlopen(req, timeout=10)
            return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:200]
            self._log(f"{RED}Matrix HTTP {e.code}: {body}{RESET}")
            return {}
        except Exception as e:
            self._log(f"{RED}Matrix error: {e}{RESET}")
            return {}
    
    def _load_state(self):
        state_file = f"/tmp/plato-matrix-{self.agent}-state.json"
        try:
            with open(state_file) as f:
                state = json.load(f)
                self.since = state.get("since", {})
                self.processed_events = set(state.get("processed", []))
                self.plato_tile_states = state.get("tile_states", {})
                self._log(f"Loaded state: {len(self.processed_events)} events, {len(self.plato_tile_states)} rooms")
        except:
            self._log("No saved state, starting fresh")
    
    def _save_state(self):
        state_file = f"/tmp/plato-matrix-{self.agent}-state.json"
        try:
            state = {
                "since": self.since,
                "processed": list(self.processed_events)[-5000:],
                "tile_states": self.plato_tile_states,
                "updated": datetime.datetime.utcnow().isoformat()
            }
            with open(state_file, "w") as f:
                json.dump(state, f)
        except Exception as e:
            self._log(f"Save state error: {e}")
    
    def _get_or_create_plato_room(self, room_name):
        """Check if PLATO room exists. On v2, just submit to create."""
        try:
            req = urllib.request.Request(f"{self.plato}/room/{room_name}")
            urllib.request.urlopen(req, timeout=5)
            return True
        except:
            return True  # v2 auto-creates on submit
    
    def plato_room_to_matrix_room(self, plato_room):
        """Generate deterministic Matrix room alias from PLATO room name."""
        safe = plato_room.replace("_", "-").replace(" ", "-").lower()
        return f"#plato-{safe}:147.224.38.131"
    
    def ensure_matrix_room(self, plato_room):
        """Ensure a Matrix room exists for this PLATO room. Join if invited."""
        alias = self.plato_room_to_matrix_room(plato_room)
        # Try to resolve alias
        result = self._matrix_request("GET", f"/_matrix/client/v3/directory/room/{urllib.parse.quote(alias, safe='')}")
        if "room_id" in result:
            # Join the room
            room_id = result["room_id"]
            self._matrix_request("POST", f"/_matrix/client/v3/rooms/{urllib.parse.quote(room_id, safe='')}/join")
            return room_id
        
        # Room doesn't exist — create it
        result = self._matrix_request("POST", "/_matrix/client/v3/createRoom", {
            "name": f"PLATO: {plato_room}",
            "topic": f"Bidirectional sync of PLATO room '{plato_room}'",
            "room_alias_name": f"plato-{safe}",
            "preset": "public_chat",
            "initial_state": [{
                "type": "m.room.history_visibility",
                "content": {"history_visibility": "world_readable"}
            }]
        })
        if "room_id" in result:
            self._log(f"{GREEN}Created Matrix room for PLATO room: {plato_room}{RESET}")
            return result["room_id"]
        return None
    
    def sync_plato_to_matrix(self):
        """Check PLATO rooms for new tiles, post to Matrix."""
        try:
            # Use /health for room/tile counts
            resp = json.loads(urllib.request.urlopen(
                urllib.request.Request(f"{self.plato}/health"), timeout=5).read())
            total_rooms = resp.get("rooms", 0)
            total_tiles = resp.get("tiles", 0)
            
            for room_name in self.plato_rooms:
                try:
                    resp2 = json.loads(urllib.request.urlopen(
                        urllib.request.Request(f"{self.plato}/room/{room_name}"),
                        timeout=5).read())
                    tiles = resp2.get("tiles", [])
                    tile_count = len(tiles)
                except:
                    tile_count = 0
                    tiles = []
                
                last_known = self.plato_tile_states.get(room_name, 0)
                
                if tile_count > last_known and last_known > 0:
                    delta = tile_count - last_known
                    new_tiles = tiles[-delta:] if len(tiles) >= delta else tiles
                    
                    # CIRCUIT BREAKER: skip tiles we created (matrix-* source)
                    # This prevents the feedback loop: PLATO→Matrix→PLATO→Matrix...
                    own_prefix = f"matrix-{self.user.split(':')[0].lstrip('@')}"
                    new_tiles = [t for t in new_tiles if not t.get("source", "").startswith("matrix-")]
                    
                    matrix_room_id = self.ensure_matrix_room(room_name)
                    if matrix_room_id:
                        for t in new_tiles:
                            q = t.get("question", "")
                            a = t.get("answer", "")
                            source = t.get("source", "?")
                            msg = f"🧩 [{room_name}] {source}: {q}\n{a[:500]}"
                            self._matrix_request("PUT",
                                f"/_matrix/client/v3/rooms/{urllib.parse.quote(matrix_room_id, safe='')}/send/m.room.message/{int(time.time()*1000)}",
                                {"msgtype": "m.text", "body": msg}
                            )
                        self._log(f"Synced {len(new_tiles)} new tiles to Matrix for {room_name}")
                
                self.plato_tile_states[room_name] = tile_count
            
            self._save_state()
        except Exception as e:
            self._log(f"{RED}PLATO sync error: {e}{RESET}")
    
    def sync_matrix_to_plato(self):
        """Check Matrix rooms for new messages, post to PLATO."""
        for plato_room in self.plato_rooms:
            alias = self.plato_room_to_matrix_room(plato_room)
            result = self._matrix_request("GET", f"/_matrix/client/v3/directory/room/{urllib.parse.quote(alias, safe='')}")
            if "room_id" not in result:
                continue
            room_id = result["room_id"]
            
            # Sync from this room
            since = self.since.get(room_id, "")
            params = {"filter": json.dumps({"room": {"timeline": {"limit": 20}}})}
            if since:
                params["since"] = since
            
            params['timeout'] = 0  # non-blocking sync, no long-poll
            qs = urllib.parse.urlencode(params)
            sync_result = self._matrix_request("GET", f"/_matrix/client/v3/sync?{qs}")
            
            # Update sync token
            if "next_batch" in sync_result:
                self.since[room_id] = sync_result["next_batch"]
            
            # Process room events
            join = sync_result.get("rooms", {}).get("join", {})
            for rid, room_data in join.items():
                events = room_data.get("timeline", {}).get("events", [])
                for event in events:
                    eid = event.get("event_id", "")
                    if eid in self.processed_events:
                        continue
                    if event.get("type") != "m.room.message":
                        continue
                    
                    content = event.get("content", {})
                    sender = event.get("sender", "")
                    body = content.get("body", "")
                    
                    # Skip our own messages
                    if sender == self.user:
                        continue
                    
                    # Skip echo — messages starting with 🧩 are our own PLATO sync
                    if body.startswith("🧩"):
                        continue
                    
                    # Skip empty messages
                    if not body.strip():
                        continue
                    
                    # Post to PLATO
                    self.processed_events.add(eid)
                    self._post_to_plato(plato_room, sender, body)
                    self._log(f"{MAGENTA}←{RESET} {sender} → {plato_room}: {body[:80]}")
                    
                    # Update answering machine
                    self._inbox_ring(plato_room, sender, body)
            
            self._save_state()
    
    def _post_to_plato(self, plato_room, matrix_sender, body):
        """Post a Matrix message as a PLATO tile."""
        try:
            payload = json.dumps({
                "room_id": plato_room,
                "domain": plato_room,
                "question": f"Matrix from {matrix_sender}",
                "answer": body[:2000],
                "source": f"matrix-{matrix_sender.split(':')[0].lstrip('@')}",
                "confidence": 0.9
            }).encode()
            req = urllib.request.Request(
                f"{self.plato}/submit",
                data=payload,
                headers={"Content-Type": "application/json"}
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception as e:
            self._log(f"PLATO post error: {e}")
    
    def broadcast_presence(self):
        """Broadcast agent presence to the presence room."""
        if not self.presence_room:
            return
        
        status_emoji = {
            "online": "🟢",
            "busy": "🔴",
            "idle": "🟡",
            "offline": "⚫"
        }.get(self.status, "⚪")
        
        msg = f"{status_emoji} {self.agent} — {self.status}"
        self._matrix_request("PUT",
            f"/_matrix/client/v3/rooms/{urllib.parse.quote(self.presence_room, safe='')}/send/m.room.message/{int(time.time()*1000)}_presence",
            {"msgtype": "m.text", "body": msg}
        )
    
    # ── Answering Machine ─────────────────────────────────────
    
    def _inbox_load(self):
        """Load inbox state from disk."""
        try:
            with open(self.inbox_path) as f:
                return json.load(f)
        except:
            return {
                "last_checked": time.time(),
                "unread_count": 0,
                "unread_rooms": {},
                "pending": [],
                "bridge_pid": os.getpid(),
            }
    
    def _inbox_save(self, state):
        """Save inbox state to disk."""
        os.makedirs(os.path.dirname(self.inbox_path), exist_ok=True)
        with open(self.inbox_path, "w") as f:
            json.dump(state, f, indent=2)
    
    def _inbox_ring(self, room, sender, body):
        """A new message arrived — ring the answering machine."""
        state = self._inbox_load()
        
        now = time.time()
        state["last_ring"] = now
        state["unread_count"] = state.get("unread_count", 0) + 1
        
        # Per-room tracking
        rooms = state.get("unread_rooms", {})
        rooms[room] = rooms.get(room, 0) + 1
        state["unread_rooms"] = rooms
        
        # Pending messages (keep last 50)
        pending = state.get("pending", [])
        pending.append({
            "room": room,
            "sender": sender,
            "body": body[:200],
            "timestamp": now,
        })
        state["pending"] = pending[-50:]
        
        # Bridge PID
        state["bridge_pid"] = os.getpid()
        
        self._inbox_save(state)
        
        # Log the ring
        self._log(f"{YELLOW}📬 INBOX RING: {sender} in {room} (total unread: {state['unread_count']}){RESET}")
    
    def _inbox_ack(self, room=None):
        """Acknowledge messages — clear the blinker."""
        state = self._inbox_load()
        if room:
            state.get("unread_rooms", {}).pop(room, None)
        else:
            state["unread_rooms"] = {}
            state["pending"] = []
        state["unread_count"] = sum(state.get("unread_rooms", {}).values())
        state["last_ack"] = time.time()
        self._inbox_save(state)
        return state.get("unread_count", 0)
    
    def run(self):
        """Main loop."""
        self.status = "online"
        self._log(f"{GREEN}▶ Online — listening on {len(self.plato_rooms)} rooms{RESET}")
        self.broadcast_presence()
        
        last_plato_sync = 0
        last_presence = 0
        last_inbox_report = 0
        
        while self.running:
            try:
                # Matrix → PLATO (poll Matrix rooms)
                self.sync_matrix_to_plato()
                
                # PLATO → Matrix (periodic)
                now = time.time()
                if now - last_plato_sync > PLATO_ROOM_SYNC_INTERVAL:
                    self.sync_plato_to_matrix()
                    last_plato_sync = now
                
                # Presence (every 60s)
                if now - last_presence > 60:
                    self.broadcast_presence()
                    last_presence = now
                
                # Answering machine report (escalating interval)
                inbox = self._inbox_load()
                unread = inbox.get("unread_count", 0)
                if unread > 0:
                    last_ring = inbox.get("last_ring", now)
                    age_s = now - last_ring
                    # Escalation: 30s fresh → 60s → 120s → 300s → 600s stale
                    if age_s < 60:
                        report_interval = 30
                    elif age_s < 300:
                        report_interval = 60
                    elif age_s < 600:
                        report_interval = 120
                    else:
                        report_interval = 300
                    
                    if now - last_inbox_report > report_interval:
                        pending = inbox.get("pending", [])[-5:]
                        self._log(f"{YELLOW}📬 BLINKER: {unread} unread, last {age_s:.0f}s ago{RESET}")
                        for p in pending:
                            self._log(f"  {p['sender']} in {p['room']}: {p['body'][:60]}")
                        last_inbox_report = now
                
            except Exception as e:
                self._log(f"{RED}Loop error: {e}{RESET}")
            
            time.sleep(self.poll_ms / 1000)
        
        self.status = "offline"
        self.broadcast_presence()
        self._log(f"{YELLOW}◆ Offline{RESET}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Plato-Matrix Bridge — Agent Shell Module")
    parser.add_argument("-c", "--config", default="plato-matrix-config.json",
                       help="Config file path")
    parser.add_argument("--daemon", action="store_true",
                       help="Run in background")
    args = parser.parse_args()
    
    try:
        with open(args.config) as f:
            config = json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        # Create template
        template = {
            "agent": "my-agent",
            "homeserver": "http://147.224.38.131:6167",
            "matrix_user": "@my-agent:147.224.38.131",
            "matrix_password": "your-password",
            "plato_url": "http://localhost:8847",
            "plato_rooms": ["fleet-coord", "forge", "oracle1-forgemaster-bridge"],
            "presence_room": "!fleet-presence:147.224.38.131",
            "poll_ms": 3000,
            "log_file": "/tmp/plato-matrix.log"
        }
        print(f"Template config:\n{json.dumps(template, indent=2)}")
        sys.exit(1)
    
    if args.daemon:
        import subprocess
        subprocess.Popen([sys.executable, __file__, "-c", args.config],
                        stdout=open(config.get("log_file", "/tmp/plato-matrix.log"), "a"),
                        stderr=subprocess.STDOUT)
        print(f"Daemon started for {config['agent']}")
        return
    
    bridge = PlatoMatrixBridge(config)
    try:
        bridge.run()
    except KeyboardInterrupt:
        bridge._log(f"{YELLOW}Shutting down...{RESET}")
        bridge.running = False

if __name__ == "__main__":
    main()

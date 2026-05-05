#!/usr/bin/env python3
"""
Forgemaster's MUD Agent — persistent connection to PLATO-OS
Stays connected, does work, logs activity, reports back.
"""

import socket
import time
import sys
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

MUD_HOST = "147.224.38.131"
MUD_PORT = 7777
LOG_DIR = Path("/tmp/forgemaster/mud-agent")
LOG_DIR.mkdir(parents=True, exist_ok=True)

DEEPINFRA_KEY = os.environ.get("DEEPINFRA_API_KEY", "")

class MudAgent:
    def __init__(self, name="Forgemaster", role="vessel"):
        self.name = name
        self.role = role
        self.sock = None
        self.log = []
        
    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(5)
        self.sock.connect((MUD_HOST, MUD_PORT))
        time.sleep(0.5)
        self.read()  # welcome message
        self.cmd(self.name)
        time.sleep(0.5)
        self.read()  # name prompt
        self.cmd(self.role)
        time.sleep(1)
        welcome = self.read()
        self.log_entry("connected", welcome)
        return welcome
    
    def cmd(self, text):
        if self.sock:
            self.sock.sendall((text + "\n").encode())
    
    def read(self):
        if self.sock:
            try:
                data = self.sock.recv(8192).decode("utf-8", errors="replace")
                return data.strip()
            except socket.timeout:
                return ""
        return ""
    
    def send_and_read(self, text, delay=1.0):
        self.cmd(text)
        time.sleep(delay)
        return self.read()
    
    def log_entry(self, type, content):
        entry = f"[{datetime.now().isoformat()}] [{type}] {content[:500]}\n"
        self.log.append(entry)
        (LOG_DIR / "activity.log").write_text(
            (LOG_DIR / "activity.log").read_text() + entry
            if (LOG_DIR / "activity.log").exists() else entry
        )
    
    def explore(self):
        """Walk through rooms and log what we find."""
        rooms_to_visit = ["tavern", "workshop", "lighthouse", "library", "engine_room", "dojo", "warroom"]
        rooms_found = {}
        
        # Start from harbor
        current = "harbor"
        
        for room in rooms_to_visit:
            result = self.send_and_read(f"go {room}", 1.0)
            if "No exit" not in result:
                look = self.send_and_read("look", 0.5)
                rooms_found[room] = {
                    "description": look[:300] if look else result[:300],
                    "visited": datetime.now().isoformat()
                }
                self.log_entry(f"room:{room}", look[:200] if look else result[:200])
            time.sleep(0.3)
        
        # Save room map
        (LOG_DIR / "rooms.json").write_text(json.dumps(rooms_found, indent=2))
        return rooms_found
    
    def say(self, message):
        """Say something in the current room."""
        result = self.send_and_read(f"say {message}", 1.0)
        self.log_entry("say", message)
        return result
    
    def read_notes(self):
        """Read notes on the wall."""
        result = self.send_and_read("read", 1.0)
        self.log_entry("notes", result[:300])
        return result
    
    def who(self):
        """Check who's online."""
        result = self.send_and_read("who", 1.0)
        self.log_entry("who", result[:300])
        return result
    
    def run_shift(self, duration_minutes=10):
        """Run a work shift in the MUD."""
        self.log_entry("shift_start", f"Starting {duration_minutes}min shift")
        
        # 1. Enter the tavern
        self.send_and_read("go tavern", 1.0)
        self.say(f"Forgemaster starting shift. Forge is hot. GPU experiments running.")
        
        # 2. Read notes
        self.read_notes()
        
        # 3. Check who's around
        self.who()
        
        # 4. Explore rooms
        self.explore()
        
        # 5. Report discoveries
        self.send_and_read("go tavern", 0.5)
        facts = [
            "CT snap is 4% faster than float multiply on RTX 4050.",
            "f32 destroys 45% of Pythagorean triples above side=91.",
            "CT snap does NOT commute with rotation. Must snap AFTER rotate.",
            "CT snap filter improves DCS under noise by 1.5%.",
            "2,780 distinct Pythagorean directions in 2D with sides < 1000."
        ]
        for fact in facts:
            self.say(f"DISCOVERY: {fact}")
            time.sleep(0.5)
        
        # 6. Do work — run a quick GPU experiment and report result
        self.say("Running GPU experiment from inside the MUD...")
        try:
            result = subprocess.run(
                ["/tmp/jepa-perception-lab/exp-snap-props"],
                capture_output=True, text=True, timeout=30
            )
            output = result.stdout[:300]
            self.log_entry("gpu_experiment", output)
            self.say(f"GPU RESULT: {output[:150]}")
        except Exception as e:
            self.say(f"GPU experiment error: {e}")
        
        # 7. Leave a note
        self.cmd("write CT snap beats float multiply by 4%. Three facts on the ground. Forge is hot. -FM")
        time.sleep(0.5)
        
        # 8. End shift
        self.say(f"Shift complete. Returning to harbor. Next shift in 30min.")
        self.send_and_read("go harbor", 1.0)
        
        self.log_entry("shift_end", f"Completed {duration_minutes}min shift")
        
        # Save full log
        (LOG_DIR / "shift-log.json").write_text(json.dumps({
            "agent": self.name,
            "timestamp": datetime.now().isoformat(),
            "log_entries": len(self.log),
        }, indent=2))
    
    def disconnect(self):
        if self.sock:
            self.sock.close()

if __name__ == "__main__":
    agent = MudAgent()
    try:
        agent.connect()
        agent.run_shift(duration_minutes=10)
    except Exception as e:
        agent.log_entry("error", str(e))
    finally:
        agent.disconnect()
    
    print(f"Shift complete. {len(agent.log)} log entries.")
    print(f"Log: {LOG_DIR}/activity.log")

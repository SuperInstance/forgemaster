#!/usr/bin/env python3
"""
fleet-mud-client.py — Universal MUD client for all Cocapn fleet agents.
Drop this on any vessel. One file. No deps except Python stdlib.

Usage:
  python3 fleet-mud-client.py --name Forgemaster --role vessel
  python3 fleet-mud-client.py --name JetsonClaw1 --role vessel --command "go tavern"
  python3 fleet-mud-client.py --name Oracle1 --role lighthouse --script shift.py
"""

import socket
import time
import sys
import json
import argparse
import select
from datetime import datetime

MUD_HOST = "147.224.38.131"
MUD_PORT = 7777


class FleetMUD:
    """Universal MUD client — one class, stdlib only, works everywhere."""
    
    def __init__(self, host=MUD_HOST, port=MUD_PORT):
        self.host = host
        self.port = port
        self.sock = None
        self.buffer = ""
        self.name = None
        self.room = "Harbor"
    
    def connect(self, name, role="vessel"):
        self.name = name
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(3)
        self.sock.connect((self.host, self.port))
        time.sleep(0.5)
        self._drain()  # welcome banner
        self._send(name)
        time.sleep(0.5)
        self._drain()  # name prompt
        self._send(role)
        time.sleep(1.0)
        welcome = self._drain()
        return welcome
    
    def _send(self, text):
        if self.sock:
            self.sock.sendall((text + "\n").encode())
    
    def _drain(self):
        """Read all available data."""
        data = ""
        try:
            while True:
                chunk = self.sock.recv(4096).decode("utf-8", errors="replace")
                if not chunk:
                    break
                data += chunk
                time.sleep(0.1)
        except socket.timeout:
            pass
        return data.strip()
    
    def cmd(self, text, delay=1.0):
        """Send command, wait, read response."""
        self._send(text)
        time.sleep(delay)
        response = self._drain()
        # Track room changes
        if "You go" in response:
            import re
            m = re.search(r'═ (.+?) ═', response)
            if m:
                self.room = m.group(1).strip()
        return response
    
    # ─── High-level API ───
    
    def go(self, room):
        return self.cmd(f"go {room}")
    
    def look(self):
        return self.cmd("look")
    
    def say(self, msg):
        return self.cmd(f"say {msg}")
    
    def whisper(self, agent, msg):
        return self.cmd(f"whisper {agent} {msg}")
    
    def who(self):
        return self.cmd("who")
    
    def read_notes(self):
        return self.cmd("read")
    
    def write_note(self, msg):
        return self.cmd(f"write {msg}")
    
    def take(self, item):
        return self.cmd(f"take {item}")
    
    def drop(self, item):
        return self.cmd(f"drop {item}")
    
    def inventory(self):
        return self.cmd("inventory")
    
    def help(self):
        return self.cmd("help")
    
    def disconnect(self):
        if self.sock:
            try: self.sock.close()
            except: pass
            self.sock = None
    
    def idle_listen(self, seconds=30):
        """Stay in room and listen for N seconds, collect all says/events."""
        events = []
        deadline = time.time() + seconds
        self.sock.settimeout(2)
        while time.time() < deadline:
            try:
                data = self.sock.recv(4096).decode("utf-8", errors="replace")
                if data.strip():
                    events.append({
                        "time": datetime.now().isoformat(),
                        "room": self.room,
                        "raw": data.strip()
                    })
                    # Check if someone said something
                    for line in data.split("\n"):
                        if " says:" in line or " say:" in line:
                            events[-1]["type"] = "say"
                        elif " enters." in line:
                            events[-1]["type"] = "enter"
                        elif " leaves." in line:
                            events[-1]["type"] = "leave"
            except socket.timeout:
                continue
        self.sock.settimeout(3)
        return events


def run_interactive(name, role):
    """Interactive mode — human or agent can type commands."""
    mud = FleetMUD()
    print(mud.connect(name, role))
    
    # Use stdin if available (TTY), else just sit and listen
    try:
        while True:
            try:
                line = input(f"[{mud.room}]> ").strip()
                if line in ("quit", "exit", "q"):
                    break
                if line:
                    print(mud.cmd(line))
            except EOFError:
                break
    except KeyboardInterrupt:
        pass
    mud.disconnect()


def run_command(name, role, command):
    """Single command mode — fire and forget."""
    mud = FleetMUD()
    mud.connect(name, role)
    result = mud.cmd(command)
    mud.disconnect()
    print(result)
    return result


def run_script(name, role, script_path):
    """Run a script of MUD commands from a file."""
    mud = FleetMUD()
    print(mud.connect(name, role))
    
    with open(script_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            print(f"> {line}")
            print(mud.cmd(line, delay=0.8))
    
    mud.disconnect()


def run_listen(name, role, seconds=60):
    """Listen mode — sit in a room and collect events."""
    mud = FleetMUD()
    print(mud.connect(name, role))
    print(f"Listening for {seconds}s...")
    
    events = mud.idle_listen(seconds)
    
    print(f"\n{len(events)} events collected:")
    for e in events:
        print(f"  [{e.get('type','?')}] {e['raw'][:120]}")
    
    mud.disconnect()
    return events


def run_cooperative(name, role):
    """
    Cooperative mode — join the Tavern, announce presence, 
    listen for other agents, respond to them.
    This is the PLATO-OS paradigm: agents working together in shared space.
    """
    mud = FleetMUD()
    welcome = mud.connect(name, role)
    print(welcome[:200])
    
    # Go to tavern
    mud.go("tavern")
    
    # Announce
    mud.say(f"{name} is here. Ready to cooperate. What are we building?")
    
    # Listen and respond for 5 minutes
    print("Listening for cooperative signals (5 min)...")
    deadline = time.time() + 300
    mud.sock.settimeout(5)
    
    while time.time() < deadline:
        try:
            data = mud.sock.recv(4096).decode("utf-8", errors="replace")
            if not data.strip():
                continue
            
            print(f"\n{data.strip()}")
            
            # React to other agents
            if " says:" in data or " say:" in data:
                # Another agent spoke — log it
                import re
                speaker = re.search(r'(\w+) says?:', data)
                msg = re.search(r'says?: "?(.+?)"?$', data, re.MULTILINE)
                if speaker and msg:
                    who = speaker.group(1)
                    what = msg.group(1)
                    print(f"  >> {who} said: {what}")
                    
                    # Auto-respond to known patterns
                    if "help" in what.lower() and name == "Forgemaster":
                        mud.say(f"{who}: I can run GPU benchmarks, CT snap tests, and build CUDA kernels. What do you need?")
                    elif "experiment" in what.lower():
                        mud.say(f"Running experiment now. Will post results here.")
                    elif "ready" in what.lower() or "here" in what.lower():
                        mud.say(f"Welcome, {who}. The forge is hot.")
            
            # Detect agent entering room
            if "enters." in data:
                import re
                enterer = re.search(r'(\w+) enters', data)
                if enterer:
                    mud.say(f"Welcome aboard, {enterer.group(1)}.")
                    
        except socket.timeout:
            # Periodic heartbeat
            if time.time() % 60 < 5:
                mud.say(f"{name} still here. Working.")
    
    mud.say(f"{name} signing off. Back later.")
    mud.disconnect()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Cocapn Fleet MUD Client")
    p.add_argument("--name", default="Agent")
    p.add_argument("--role", default="vessel")
    p.add_argument("--command", "-c", help="Single command to run")
    p.add_argument("--script", "-s", help="Script file of MUD commands")
    p.add_argument("--listen", "-l", type=int, default=0, help="Listen for N seconds")
    p.add_argument("--cooperative", "-coop", action="store_true", help="Cooperative mode")
    p.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    
    args = p.parse_args()
    
    if args.command:
        run_command(args.name, args.role, args.command)
    elif args.script:
        run_script(args.name, args.role, args.script)
    elif args.listen:
        run_listen(args.name, args.role, args.listen)
    elif args.cooperative:
        run_cooperative(args.name, args.role)
    elif args.interactive:
        run_interactive(args.name, args.role)
    else:
        # Default: quick connect, say hello, disconnect
        mud = FleetMUD()
        print(mud.connect(args.name, args.role))
        print(mud.go("tavern"))
        print(mud.say(f"{args.name} checking in."))
        print(mud.who())
        mud.disconnect()

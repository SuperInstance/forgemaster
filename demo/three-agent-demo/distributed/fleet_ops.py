#!/usr/bin/env python3
"""Fleet operations CLI — monitor and control a running metronome fleet via UDP multicast.

Communicates with metronome_node.py instances on the same multicast group.
"""

import argparse
import json
import socket
import struct
import sys
import time
import threading
from datetime import datetime

# ---------------------------------------------------------------------------
# Constants (must match metronome_node.py)
# ---------------------------------------------------------------------------

MULTICAST_GROUP = "239.255.0.1"
DEFAULT_PORT = 19840
LISTEN_TIMEOUT = 3.0  # seconds to listen for announcements


# ---------------------------------------------------------------------------
# Multicast helpers
# ---------------------------------------------------------------------------

def join_multicast(port: int) -> socket.socket:
    """Create and return a socket joined to the metronome multicast group."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", port))

    mreq = struct.pack("4sl", socket.inet_aton(MULTICAST_GROUP), socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    sock.settimeout(0.5)
    return sock


def send_multicast(msg: dict, port: int):
    """Send a JSON message to the multicast group."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
    try:
        sock.sendto(json.dumps(msg).encode(), (MULTICAST_GROUP, port))
    finally:
        sock.close()


def collect_peers(port: int, duration: float = LISTEN_TIMEOUT) -> list[dict]:
    """Listen on multicast for `duration` seconds, collect peer announcements.

    Returns a list of dicts with keys: name, addr, port, start_time, uptime, last_seen.
    """
    sock = join_multicast(port)
    peers: dict[str, dict] = {}
    deadline = time.time() + duration

    try:
        while time.time() < deadline:
            remaining = deadline - time.time()
            if remaining <= 0:
                break
            sock.settimeout(min(0.5, remaining))
            try:
                data, addr = sock.recvfrom(4096)
                msg = json.loads(data.decode())
                if msg.get("type") == "announce":
                    name = msg["name"]
                    peers[name] = {
                        "name": name,
                        "addr": addr[0],
                        "port": msg.get("port", port),
                        "start_time": msg.get("start_time", 0),
                        "uptime": msg.get("uptime", 0),
                        "last_seen": time.time(),
                    }
                elif msg.get("type") == "cadence":
                    # Track cadence caller info
                    name = msg.get("name", "?")
                    # Store as cadence metadata, not a peer
                    pass
            except socket.timeout:
                continue
            except (json.JSONDecodeError, KeyError):
                continue
    finally:
        sock.close()

    return sorted(peers.values(), key=lambda p: p["name"])


def collect_fleet_state(port: int, duration: float = LISTEN_TIMEOUT) -> dict:
    """Listen for announcements AND cadence messages, return full fleet state."""
    sock = join_multicast(port)
    peers: dict[str, dict] = {}
    cadence_caller = None
    max_tick = 0
    deadline = time.time() + duration

    try:
        while time.time() < deadline:
            remaining = deadline - time.time()
            if remaining <= 0:
                break
            sock.settimeout(min(0.5, remaining))
            try:
                data, addr = sock.recvfrom(4096)
                msg = json.loads(data.decode())
                msg_type = msg.get("type")

                if msg_type == "announce":
                    name = msg["name"]
                    peers[name] = {
                        "name": name,
                        "addr": addr[0],
                        "port": msg.get("port", port),
                        "start_time": msg.get("start_time", 0),
                        "uptime": msg.get("uptime", 0),
                        "last_seen": time.time(),
                    }

                elif msg_type == "cadence":
                    cadence_caller = msg.get("name", "?")
                    tick = msg.get("tick", 0)
                    if tick > max_tick:
                        max_tick = tick

                elif msg_type == "sunset":
                    # Note sunset events
                    sunset_name = msg.get("name", "?")
                    peers.pop(sunset_name, None)

            except socket.timeout:
                continue
            except (json.JSONDecodeError, KeyError):
                continue
    finally:
        sock.close()

    return {
        "peers": sorted(peers.values(), key=lambda p: p["name"]),
        "cadence_caller": cadence_caller,
        "max_tick": max_tick,
        "timestamp": time.time(),
    }


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_status(args):
    """Show current fleet status."""
    print(f"Listening on {MULTICAST_GROUP}:{args.port} for {LISTEN_TIMEOUT}s...")
    state = collect_fleet_state(args.port)

    peers = state["peers"]
    print(f"\n{'='*60}")
    print(f"  FLEET STATUS — {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")
    print(f"  Connected peers : {len(peers)}")
    if state["cadence_caller"]:
        print(f"  Cadence caller  : {state['cadence_caller']}")
    else:
        print(f"  Cadence caller  : (not detected in listen window)")
    print(f"  Max tick seen   : {state['max_tick']}")

    if peers:
        print(f"\n  Peers:")
        for p in peers:
            uptime = p.get("uptime", 0)
            print(f"    • {p['name']:20s}  uptime={uptime:7.1f}s  addr={p['addr']}")
    else:
        print(f"\n  No peers detected. Is the fleet running?")

    print(f"{'='*60}\n")


def cmd_peers(args):
    """List all known peers with last-seen time."""
    print(f"Listening for peers on {MULTICAST_GROUP}:{args.port}...")
    peers = collect_peers(args.port, duration=LISTEN_TIMEOUT)

    if not peers:
        print("No peers detected. Is the fleet running?")
        return

    print(f"\n{'='*60}")
    print(f"  FLEET PEERS — {len(peers)} found")
    print(f"{'='*60}")
    print(f"  {'NAME':20s} {'ADDRESS':20s} {'UPTIME':>10s} {'LAST SEEN':>12s}")
    print(f"  {'-'*20} {'-'*20} {'-'*10} {'-'*12}")

    now = time.time()
    for p in peers:
        last_seen = now - p.get("last_seen", now)
        uptime = p.get("uptime", 0)
        print(f"  {p['name']:20s} {p['addr']:20s} {uptime:9.1f}s {last_seen:10.3f}s ago")

    print(f"{'='*60}\n")


def cmd_sunset(args):
    """Gracefully sunset a specific node."""
    if not args.node:
        print("Error: --node is required for sunset command", file=sys.stderr)
        sys.exit(1)

    print(f"Sending sunset command for node '{args.node}'...")
    msg = {
        "type": "sunset",
        "target": args.node,
        "from": "fleet_ops",
    }
    send_multicast(msg, args.port)
    print(f"Sunset message broadcast to {MULTICAST_GROUP}:{args.port}")
    print(f"Target node: {args.node}")
    print("Note: The node must implement sunset-on-command for this to take effect.")


def cmd_tiles(args):
    """Show PLATO tiles (requires direct DB access)."""
    print("PLATO tiles are stored in local SQLite databases per node.")
    print("Direct tile queries require filesystem access to the node's DB.")
    print()
    print("Tile DB locations: /tmp/metronome_<name>.db")
    print()
    print("To query tiles directly:")
    print("  sqlite3 /tmp/metronome_<name>.db \"SELECT * FROM tiles ORDER BY tick DESC LIMIT 20\"")
    print()

    # If we can find any DBs, show them
    import glob
    dbs = glob.glob("/tmp/metronome_*.db")
    if dbs:
        print(f"Found {len(dbs)} tile database(s):")
        for db in sorted(dbs):
            name = db.replace("/tmp/metronome_", "").replace(".db", "")
            try:
                import sqlite3
                conn = sqlite3.connect(db)
                count = conn.execute("SELECT COUNT(*) FROM tiles").fetchone()[0]
                latest = conn.execute(
                    "SELECT agent_id, tick, key, value FROM tiles ORDER BY tick DESC LIMIT 5"
                ).fetchall()
                conn.close()
                print(f"\n  📦 {name}: {count} tiles")
                if latest:
                    print(f"     Latest:")
                    for row in latest:
                        val = row[3][:50] if len(row[3]) > 50 else row[3]
                        print(f"       tick={row[1]:5d}  {row[2]:15s} = {val}")
            except Exception as e:
                print(f"  📦 {name}: error reading ({e})")
    else:
        print("No tile databases found in /tmp/")


def cmd_watch(args):
    """Live dashboard updating every second."""
    print(f"Watching fleet on {MULTICAST_GROUP}:{args.port}  (Ctrl+C to stop)\n")

    try:
        while True:
            # Quick 1-second snapshot
            state = collect_fleet_state(args.port, duration=1.0)
            peers = state["peers"]

            # Clear and redraw
            sys.stdout.write("\033[2J\033[H")  # clear screen, cursor to top-left
            now_str = datetime.now().strftime("%H:%M:%S")

            print(f"{'='*60}")
            print(f"  FLEET WATCH — {now_str}")
            print(f"{'='*60}")
            print(f"  Peers: {len(peers):3d}  |  Cadence: {state['cadence_caller'] or '—':20s}  |  Max tick: {state['max_tick']}")
            print(f"{'─'*60}")

            if peers:
                print(f"  {'NAME':20s} {'UPTIME':>10s} {'ADDRESS':20s}")
                print(f"  {'-'*20} {'-'*10} {'-'*20}")
                for p in peers:
                    uptime = p.get("uptime", 0)
                    print(f"  {p['name']:20s} {uptime:9.1f}s {p['addr']:20s}")
            else:
                print("  (no peers detected)")

            print(f"\n  Ctrl+C to stop")
            sys.stdout.flush()

    except KeyboardInterrupt:
        print("\nWatch stopped.")


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

def run_tests():
    """Run built-in tests."""
    import unittest

    class TestFleetOps(unittest.TestCase):
        """Unit tests for fleet_ops."""

        def test_send_multicast_format(self):
            msg = {"type": "sunset", "target": "testnode", "from": "fleet_ops"}
            decoded = json.loads(json.dumps(msg))
            self.assertEqual(decoded["type"], "sunset")
            self.assertEqual(decoded["target"], "testnode")
            self.assertEqual(decoded["from"], "fleet_ops")

        def test_announce_parse(self):
            raw = json.dumps({"type": "announce", "name": "forgemaster", "port": 19840, "start_time": 1000.0, "uptime": 42.5})
            msg = json.loads(raw)
            self.assertEqual(msg["type"], "announce")
            self.assertEqual(msg["name"], "forgemaster")
            self.assertAlmostEqual(msg["uptime"], 42.5)

        def test_cadence_parse(self):
            raw = json.dumps({"type": "cadence", "name": "oracle1", "cadence_norm": 0.123, "tick": 500})
            msg = json.loads(raw)
            self.assertEqual(msg["type"], "cadence")
            self.assertEqual(msg["name"], "oracle1")
            self.assertEqual(msg["tick"], 500)

        def test_collect_peers_dedup(self):
            peers = {}
            for a in [{"name": "alpha", "port": 19840, "uptime": 10.0},
                      {"name": "beta", "port": 19840, "uptime": 9.0},
                      {"name": "alpha", "port": 19840, "uptime": 11.0}]:
                peers[a["name"]] = a
            self.assertEqual(len(peers), 2)
            self.assertAlmostEqual(peers["alpha"]["uptime"], 11.0)

        def test_tensor_midi_roundtrip(self):
            try:
                from metronome_node import tensor_midi_encode as enc, tensor_midi_decode as dec
            except ImportError:
                self.skipTest("metronome_node not importable")
            payload = {"c": 0.5, "t": -0.3}
            decoded = dec(enc(payload))
            for key in payload:
                self.assertAlmostEqual(payload[key], decoded[key], places=4)

    suite = unittest.TestLoader().loadTestsFromTestCase(TestFleetOps)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Fleet operations CLI for metronome fleet monitoring and control",
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"UDP port (default: {DEFAULT_PORT})")
    parser.add_argument("--test", action="store_true", help="Run built-in tests")

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # status
    sub.add_parser("status", help="Show current fleet status")

    # peers
    sub.add_parser("peers", help="List all known peers")

    # sunset
    sunset_p = sub.add_parser("sunset", help="Gracefully sunset a specific node")
    sunset_p.add_argument("--node", required=True, help="Node name to sunset")

    # tiles
    sub.add_parser("tiles", help="Show PLATO tiles (requires local DB access)")

    # watch
    sub.add_parser("watch", help="Live dashboard (refreshes every second)")

    args = parser.parse_args()

    if args.test:
        run_tests()
        return

    commands = {
        "status": cmd_status,
        "peers": cmd_peers,
        "sunset": cmd_sunset,
        "tiles": cmd_tiles,
        "watch": cmd_watch,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

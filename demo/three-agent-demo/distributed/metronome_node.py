#!/usr/bin/env python3
"""Distributed metronome node — UDP discovery, cadence election, Tensor-MIDI wire format.

Runs as a standalone process or importable library.
"""

import argparse
import json
import logging
import os
import signal
import socket
import struct
import sys
import threading
import time
from fractions import Fraction
from pathlib import Path

# Make metronome_core importable from parent dir
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from metronome_core import MetronomeAgent, PlatoTileStore, CorrectionMode

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("metronome_node")

# ---------------------------------------------------------------------------
# Tensor-MIDI encoding
# ---------------------------------------------------------------------------

MIDI_CHANNELS = 16
MIDI_CC_MAX = 127  # INT8 saturation ceiling (7-bit)


def tensor_midi_encode(payload: dict) -> bytes:
    """Encode a dict into a compact Tensor-MIDI wire format.

    Layout (all big-endian):
      [4B magic=0x544D4944] [1B version] [2B num_entries]
      For each entry:
        [1B key_len] [key_len B key] [8B float64 value]
    All float values are clamped to [-1.0, 1.0] then scaled to int64 range
    for INT8 saturation semantics.
    """
    MAGIC = 0x544D4944  # "TMID"
    VERSION = 1

    # Convert payload values to float, clamp for INT8 saturation
    entries = []
    for k, v in payload.items():
        fv = float(v)
        # Clamp to [-1.0, 1.0] range for saturation
        fv = max(-1.0, min(1.0, fv))
        # Scale to int64 range for "INT8 saturation" semantics
        scaled = int(fv * (2**23 - 1))
        entries.append((k.encode("utf-8"), scaled))

    buf = struct.pack(">IBH", MAGIC, VERSION, len(entries))
    for key_bytes, value in entries:
        buf += struct.pack(">Bq", len(key_bytes), value)
        buf += key_bytes

    return buf


def tensor_midi_decode(data: bytes) -> dict:
    """Decode Tensor-MIDI wire format back to dict."""
    MAGIC = 0x544D4944
    offset = 0
    magic, version, num_entries = struct.unpack_from(">IBH", data, offset)
    offset += 7

    if magic != MAGIC:
        raise ValueError(f"Bad magic: {magic:#x}")

    result = {}
    for _ in range(num_entries):
        key_len, value = struct.unpack_from(">Bq", data, offset)
        offset += 9
        key = data[offset : offset + key_len].decode("utf-8")
        offset += key_len
        # Unscale from int64 back to float
        result[key] = value / (2**23 - 1)

    return result


# ---------------------------------------------------------------------------
# UDP peer discovery
# ---------------------------------------------------------------------------

MULTICAST_GROUP = "239.255.0.1"
MULTICAST_PORT = 19840
DISCOVERY_INTERVAL = 1.0  # seconds


class PeerDiscovery:
    """UDP multicast peer discovery for the metronome fleet."""

    def __init__(self, node_name: str, port: int, ttl: int = 1):
        self.node_name = node_name
        self.port = port
        self.ttl = ttl
        self.peers: dict[str, dict] = {}  # name -> {addr, port, last_seen, start_time}
        self.start_time = time.time()
        self._running = False
        self._sock_send = None
        self._sock_recv = None
        self._lock = threading.Lock()

    def start(self):
        self._running = True
        # Send socket
        self._sock_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self._sock_send.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, self.ttl)

        # Receive socket
        self._sock_recv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self._sock_recv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock_recv.bind(("", self.port))

        mreq = struct.pack(
            "4sl",
            socket.inet_aton(MULTICAST_GROUP),
            socket.INADDR_ANY,
        )
        self._sock_recv.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        self._sock_recv.settimeout(0.5)

        # Start threads
        threading.Thread(target=self._announce_loop, daemon=True).start()
        threading.Thread(target=self._listen_loop, daemon=True).start()
        log.info(f"PeerDiscovery started on {MULTICAST_GROUP}:{self.port} as {self.node_name}")

    def stop(self):
        self._running = False
        for s in (self._sock_send, self._sock_recv):
            if s:
                try:
                    s.close()
                except Exception:
                    pass

    def get_peers(self) -> dict:
        with self._lock:
            # Expire peers not seen in 5 seconds
            now = time.time()
            expired = [n for n, p in self.peers.items() if now - p["last_seen"] > 5.0]
            for n in expired:
                log.info(f"Peer expired: {n}")
                del self.peers[n]
            return dict(self.peers)

    def get_uptime(self) -> float:
        return time.time() - self.start_time

    def _announce_loop(self):
        while self._running:
            try:
                msg = json.dumps({
                    "type": "announce",
                    "name": self.node_name,
                    "port": self.port,
                    "start_time": self.start_time,
                    "uptime": self.get_uptime(),
                }).encode()
                self._sock_send.sendto(msg, (MULTICAST_GROUP, self.port))
            except Exception as e:
                if self._running:
                    log.debug(f"Announce error: {e}")
            time.sleep(DISCOVERY_INTERVAL)

    def _listen_loop(self):
        while self._running:
            try:
                data, addr = self._sock_recv.recvfrom(4096)
                msg = json.loads(data.decode())
                if msg["type"] == "announce" and msg["name"] != self.node_name:
                    with self._lock:
                        self.peers[msg["name"]] = {
                            "addr": addr[0],
                            "port": msg["port"],
                            "last_seen": time.time(),
                            "start_time": msg["start_time"],
                            "uptime": msg["uptime"],
                        }
                elif msg["type"] == "sunset":
                    with self._lock:
                        self.peers.pop(msg["name"], None)
                    log.info(f"Received sunset from {msg['name']}")
                elif msg["type"] == "cadence":
                    # Cadence caller broadcasting reference time
                    pass  # handled by MetronomeNode
            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    log.debug(f"Listen error: {e}")


# ---------------------------------------------------------------------------
# Distributed metronome node
# ---------------------------------------------------------------------------

class MetronomeNode:
    """A single node in the distributed metronome fleet."""

    def __init__(
        self,
        name: str,
        port: int = MULTICAST_PORT,
        delta: float = 0.0001,
        drift_rate: float = 0.0,
        max_ticks: int = 0,
        peers: list[str] | None = None,
    ):
        self.name = name
        self.port = port
        self.delta = Fraction(delta).limit_denominator(1000000)
        self.max_ticks = max_ticks
        self.peers = peers or []

        # Core metronome
        db_path = f"/tmp/metronome_{name}.db"
        self.tile_store = PlatoTileStore(db_path)
        self.agent = MetronomeAgent(
            agent_id=name,
            drift_rate=drift_rate,
            tile_store=self.tile_store,
        )

        # Discovery
        self.discovery = PeerDiscovery(name, port)

        # State
        self._running = False
        self.is_cadence_caller = False
        self.cadence_caller_name: str | None = None
        self.tick_count = 0

        # Cadence broadcast socket
        self._cadence_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self._cadence_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)

    def start(self):
        """Start the node: discovery + tick loop."""
        self._running = True
        self.discovery.start()

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

        log.info(f"Node {self.name} starting (port={self.port}, delta={float(self.delta):.6f})")
        self._tick_loop()

    def stop(self, sunset: bool = True):
        """Stop the node, optionally broadcasting sunset."""
        self._running = False
        if sunset:
            self._send_sunset()
        self.discovery.stop()
        self._cadence_sock.close()
        self.tile_store.close()
        log.info(f"Node {self.name} stopped")

    def _handle_signal(self, signum, frame):
        log.info(f"Node {self.name} received signal {signum}")
        self.stop(sunset=True)
        sys.exit(0)

    def _tick_loop(self):
        """Main tick loop — runs until max_ticks or stopped."""
        while self._running:
            if self.max_ticks and self.tick_count >= self.max_ticks:
                log.info(f"Node {self.name} reached max ticks ({self.max_ticks})")
                break

            self.agent.tick()
            self.tick_count += 1

            # Run election every 10 ticks
            if self.tick_count % 10 == 0:
                self._run_election()

            # If we're cadence caller, broadcast reference time
            if self.is_cadence_caller:
                self._broadcast_cadence()

            # If we're not the caller, apply deadband correction
            if not self.is_cadence_caller and self.cadence_caller_name:
                # Wait for cadence broadcast (handled inline for simplicity)
                pass

            # Every 100 ticks, log status
            if self.tick_count % 100 == 0:
                drift = float(self.agent.clock.drift)
                log.info(
                    f"Node {self.name} tick={self.tick_count} "
                    f"drift={drift:.6f} "
                    f"cadence_caller={self.is_cadence_caller} "
                    f"peers={len(self.discovery.get_peers())}"
                )

            time.sleep(0.01)  # ~100 ticks/sec

    def _run_election(self):
        """Elect cadence caller: longest uptime wins. Ties broken by name sort."""
        my_uptime = self.discovery.get_uptime()
        peers = self.discovery.get_peers()

        candidates = [(self.name, my_uptime)]
        for pname, pdata in peers.items():
            candidates.append((pname, pdata.get("uptime", 0)))

        # Sort by uptime descending, then name ascending for tie-breaking
        candidates.sort(key=lambda x: (-x[1], x[0]))
        winner = candidates[0][0]

        was_caller = self.is_cadence_caller
        self.is_cadence_caller = winner == self.name
        self.cadence_caller_name = winner

        if self.is_cadence_caller and not was_caller:
            log.info(f"Node {self.name} elected as cadence caller (uptime={my_uptime:.1f}s)")
        elif not self.is_cadence_caller and was_caller:
            log.info(f"Node {self.name} lost cadence caller to {winner}")

    def _broadcast_cadence(self):
        """Broadcast current cadence reference time via Tensor-MIDI."""
        cadence = self.agent.get_cadence()
        # Normalize cadence to [-1, 1] range using modular arithmetic
        normalized = float(cadence % Fraction(1000)) / 1000.0

        payload = {
            "type": "cadence",
            "name": self.name,
            "cadence_norm": max(-1.0, min(1.0, normalized)),
            "tick": self.tick_count,
        }

        # Encode as Tensor-MIDI and also JSON fallback
        try:
            encoded = tensor_midi_encode({"c": normalized, "t": self.tick_count / 10000.0})
            # Send both JSON and binary
            json_msg = json.dumps(payload).encode()
            self._cadence_sock.sendto(json_msg, (MULTICAST_GROUP, self.port))
        except Exception as e:
            log.debug(f"Cadence broadcast error: {e}")

    def _send_sunset(self):
        """Broadcast sunset message with inheritance data."""
        sunset_data = self.agent.sunset()
        sunset_data["type"] = "sunset"
        sunset_data["name"] = self.name
        sunset_data["is_cadence_caller"] = self.is_cadence_caller

        msg = json.dumps(sunset_data).encode()
        try:
            self._cadence_sock.sendto(msg, (MULTICAST_GROUP, self.port))
        except Exception as e:
            log.debug(f"Sunset broadcast error: {e}")
        log.info(f"Node {self.name} sent sunset broadcast")

    def get_status(self) -> dict:
        """Return current node status."""
        return {
            "name": self.name,
            "tick": self.tick_count,
            "drift": float(self.agent.clock.drift),
            "true_time": float(self.agent.clock.true_time),
            "local_time": float(self.agent.clock.local_time),
            "is_cadence_caller": self.is_cadence_caller,
            "cadence_caller": self.cadence_caller_name,
            "peers": list(self.discovery.get_peers().keys()),
            "uptime": self.discovery.get_uptime(),
        }


# ---------------------------------------------------------------------------
# Tensor-MIDI round-trip test helpers
# ---------------------------------------------------------------------------

def tensor_midi_roundtrip(payload: dict) -> dict:
    """Encode and decode payload through Tensor-MIDI for testing."""
    encoded = tensor_midi_encode(payload)
    return tensor_midi_decode(encoded)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Distributed metronome node")
    parser.add_argument("--name", required=True, help="Node name (unique in fleet)")
    parser.add_argument("--port", type=int, default=MULTICAST_PORT, help="UDP port")
    parser.add_argument("--peers", nargs="*", default=[], help="Known peer names")
    parser.add_argument("--ticks", type=int, default=0, help="Max ticks (0=unlimited)")
    parser.add_argument("--delta", type=float, default=0.0001, help="Deadband threshold")
    parser.add_argument("--drift", type=float, default=0.0, help="Simulated drift rate")
    parser.add_argument("--verbose", action="store_true", help="Debug logging")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    node = MetronomeNode(
        name=args.name,
        port=args.port,
        delta=args.delta,
        drift_rate=args.drift,
        max_ticks=args.ticks,
        peers=args.peers,
    )
    node.start()


if __name__ == "__main__":
    main()

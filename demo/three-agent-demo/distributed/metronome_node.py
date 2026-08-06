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

# Import spec-compliant fleet protocol (same dir)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fleet_protocol import (
    MAGIC as FLEET_MAGIC,
    MessageType,
    encode_raw,
    decode_raw,
    encode_tick,
    encode_cadence_call,
    encode_sunset,
    encode_message,
    decode_message,
    DECODERS,
    ProtocolError,
    now_ms,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("metronome_node")

# ---------------------------------------------------------------------------
# Tensor-MIDI encoding (spec-compliant via fleet_protocol)
#
# Wire format (big-endian):
#   [4B magic=0xF1EE7] [1B type] [1B sender] [8B timestamp_ms]
#   [N bytes payload] [2B CRC16]
#
# Message types: BEACON, TICK, DRIFT_REPORT, CADENCE_CALL, CORRECTION,
#                SUNSET, INHERIT, ACK, LEAVE
# ---------------------------------------------------------------------------


def tensor_midi_encode(payload: dict) -> bytes:
    """Encode a dict into Tensor-MIDI wire format.

    Three modes:
    1. **Fleet protocol mode** — payload includes a 'type' key matching a
       MessageType name. Uses fleet_protocol encoders for full spec compliance.
    2. **TICK compat mode** — payload keys are a subset of {beat, t, c, state}.
       Maps to TICK fields: beat→beat, t→time_ms (×10000), c→drift, state→state.
    3. **Simple dict mode** — arbitrary {key: float} with values in [-1, 1].
       Encodes as a self-describing JSON blob with type tag 0.
    """
    msg_type_name = payload.get("type")
    sender_id = payload.get("sender_id", 0)
    ts = payload.get("timestamp_ms") or now_ms()

    if msg_type_name and hasattr(MessageType, msg_type_name):
        msg_type = MessageType[msg_type_name]
        kwargs = {k: v for k, v in payload.items() if k not in ("type", "sender_id", "timestamp_ms")}
        kwargs["timestamp_ms"] = ts
        return encode_message(msg_type, sender_id=sender_id, **kwargs)

    # TICK compat mode: only when payload explicitly uses TICK-specific
    # field names ("beat" or "drift") that don't collide with common keys.
    if "beat" in payload or "drift" in payload:
        beat = int(payload.get("beat", 0))
        time_ms = int(payload.get("t", 0) * 10000) if "t" in payload else 0
        drift = float(payload.get("drift", payload.get("c", 0.0)))
        state = int(payload.get("state", 0))
        return encode_tick(
            sender_id=sender_id,
            timestamp_ms=ts,
            beat=beat,
            time_ms=time_ms,
            drift=drift,
            state=state,
        )

    # Simple dict mode (includes empty payload): clamp values to [-1, 1]
    clamped = {}
    for k, v in payload.items():
        try:
            fv = float(v)
        except (TypeError, ValueError):
            fv = 0.0
        clamped[k] = max(-1.0, min(1.0, fv))
    json_bytes = json.dumps(clamped, separators=(",", ":"), sort_keys=True).encode("utf-8")
    SIMPLE_TYPE = 0  # Non-protocol type for simple dict payloads
    return encode_raw(SIMPLE_TYPE, sender_id, ts, json_bytes)


def tensor_midi_decode(data: bytes) -> dict:
    """Decode Tensor-MIDI wire format back to a dict.

    Handles both fleet-protocol messages and simple dict payloads.
    """
    raw = decode_raw(data)
    msg_type = raw["type"]

    # Simple dict mode (type 0)
    if isinstance(msg_type, int) and msg_type == 0:
        return json.loads(raw["payload"].decode("utf-8"))

    # Fleet protocol mode — delegate to per-type decoder
    decoder = DECODERS.get(msg_type)
    if decoder is None:
        raise ProtocolError(f"No decoder for {msg_type}")
    parsed = decoder(raw["payload"])
    return {
        "type": msg_type,
        "sender_id": raw["sender_id"],
        "timestamp_ms": raw["timestamp_ms"],
        "payload": parsed,
    }


def tensor_midi_roundtrip(payload: dict) -> dict:
    """Encode then decode a payload — convenience for round-trip tests."""
    return tensor_midi_decode(tensor_midi_encode(payload))


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
        """Broadcast current cadence reference time via spec-compliant Tensor-MIDI."""
        cadence = self.agent.get_cadence()
        # Normalize cadence to [-1, 1] range using modular arithmetic
        normalized = float(cadence % Fraction(1000)) / 1000.0

        try:
            encoded = encode_tick(
                sender_id=0,  # cadence caller
                timestamp_ms=now_ms(),
                beat=self.tick_count,
                time_ms=int(time.time() * 1000),
                drift=normalized,
                state=1 if self.is_cadence_caller else 0,
            )
            # Send binary Tensor-MIDI packet
            self._cadence_sock.sendto(encoded, (MULTICAST_GROUP, self.port))
        except Exception as e:
            log.debug(f"Cadence broadcast error: {e}")

    def _send_sunset(self):
        """Broadcast sunset message with inheritance data via spec-compliant Tensor-MIDI."""
        sunset_data = self.agent.sunset()

        try:
            # Encode as SUNSET message via fleet_protocol
            node_id_bytes = self.name.encode("utf-8")
            encoded = encode_sunset(
                sender_id=0,
                timestamp_ms=now_ms(),
                node_id=hash(self.name) % 256,
                tile_count=self.tick_count,
            )
            self._cadence_sock.sendto(encoded, (MULTICAST_GROUP, self.port))
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

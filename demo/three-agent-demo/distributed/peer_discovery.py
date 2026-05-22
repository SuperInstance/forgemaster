"""UDP-based peer discovery for the metronome fleet.

Each node:
  - Broadcasts BEACON every BEACON_INTERVAL seconds on multicast 239.255.0.1:19840
  - Listens for BEACONs (and LEAVEs) from other nodes
  - Maintains a peer table with last-seen timestamps
  - Detects failed peers (no BEACON for PEER_TIMEOUT seconds)
  - Supports graceful leave (LEAVE message on shutdown)
  - Handles merge when two clusters discover each other
  - Thread-safe peer table with locks
"""

from __future__ import annotations

import logging
import socket
import struct
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional, Set

from .fleet_protocol import (
    MessageType,
    decode_message,
    encode_beacon,
    encode_leave,
    now_ms,
)

logger = logging.getLogger(__name__)


@dataclass
class PeerInfo:
    """Information about a discovered peer."""

    node_id: int
    last_seen: float  # monotonic time
    uptime_ms: int
    theta: Dict
    addr: tuple  # (ip, port)
    known_peers: Set[int] = field(default_factory=set)

    @property
    def age(self) -> float:
        return time.monotonic() - self.last_seen


class PeerDiscovery:
    """Multicast UDP peer discovery with failure detection and cluster merge."""

    MULTICAST_GROUP = "239.255.0.1"
    MULTICAST_PORT = 19840
    BEACON_INTERVAL = 5.0
    PEER_TIMEOUT = 15.0
    _TTL = 1  # keep multicast on the local segment

    def __init__(
        self,
        node_id: int,
        theta: Dict,
        bind_addr: str = "0.0.0.0",
        multicast_group: Optional[str] = None,
        port: Optional[int] = None,
        on_peer_join: Optional[Callable[[PeerInfo], None]] = None,
        on_peer_leave: Optional[Callable[[int], None]] = None,
        on_merge: Optional[Callable[[Set[int]], None]] = None,
    ):
        if not (0 <= node_id <= 0xFF):
            raise ValueError(f"node_id must fit in one byte, got {node_id}")
        self.node_id = node_id
        self.theta = theta
        self.bind_addr = bind_addr
        self.multicast_group = multicast_group or self.MULTICAST_GROUP
        self.port = port or self.MULTICAST_PORT

        self._on_peer_join = on_peer_join
        self._on_peer_leave = on_peer_leave
        self._on_merge = on_merge

        # Thread-safe peer table
        self._peers: Dict[int, PeerInfo] = {}
        self._lock = threading.RLock()

        # Uptime tracking
        self._start_time = time.monotonic()

        # Threads
        self._sock: Optional[socket.socket] = None
        self._listener_thread: Optional[threading.Thread] = None
        self._beacon_thread: Optional[threading.Thread] = None
        self._janitor_thread: Optional[threading.Thread] = None
        self._running = False
        self._shutdown_event = threading.Event()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Open socket, join multicast group, and start background threads."""
        if self._running:
            return
        self._running = True

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except (AttributeError, OSError):
            pass  # Windows or older kernel
        self._sock.bind((self.bind_addr, self.port))

        # Join multicast group
        mreq = struct.pack(
            "=4sl",
            socket.inet_aton(self.multicast_group),
            socket.INADDR_ANY,
        )
        self._sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        # Threads
        self._listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._beacon_thread = threading.Thread(target=self._beacon_loop, daemon=True)
        self._janitor_thread = threading.Thread(target=self._janitor_loop, daemon=True)

        self._listener_thread.start()
        self._beacon_thread.start()
        self._janitor_thread.start()

        logger.info(
            "PeerDiscovery started node=%d group=%s:%d",
            self.node_id,
            self.multicast_group,
            self.port,
        )

    def stop(self, grace_period: float = 1.0) -> None:
        """Send LEAVE, stop threads, and close socket."""
        if not self._running:
            return
        self._running = False

        # Graceful leave
        try:
            self._send_leave()
        except Exception:
            logger.exception("Failed to send LEAVE")

        self._shutdown_event.set()
        time.sleep(grace_period)

        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

        for t in (self._listener_thread, self._beacon_thread, self._janitor_thread):
            if t and t.is_alive():
                t.join(timeout=1.0)

        logger.info("PeerDiscovery stopped node=%d", self.node_id)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False

    @property
    def local_addr(self) -> Optional[tuple]:
        """Return the bound (ip, port) of the underlying socket, or None."""
        if self._sock:
            return self._sock.getsockname()
        return None

    # ------------------------------------------------------------------
    # Peer table API (thread-safe)
    # ------------------------------------------------------------------

    def peer_ids(self) -> Set[int]:
        with self._lock:
            return set(self._peers.keys())

    def peer_count(self) -> int:
        with self._lock:
            return len(self._peers)

    def get_peer(self, node_id: int) -> Optional[PeerInfo]:
        with self._lock:
            return self._peers.get(node_id)

    def all_peers(self) -> Dict[int, PeerInfo]:
        with self._lock:
            return dict(self._peers)

    def known_peers_for_beacon(self) -> Set[int]:
        """Return the set of peer ids we currently know (for BEACON payload)."""
        with self._lock:
            return set(self._peers.keys())

    # ------------------------------------------------------------------
    # Networking
    # ------------------------------------------------------------------

    def _uptime_ms(self) -> int:
        return int((time.monotonic() - self._start_time) * 1000)

    def _send_leave(self) -> None:
        if self._sock is None:
            return
        ts = now_ms()
        pkt = encode_leave(sender_id=self.node_id, timestamp_ms=ts, node_id=self.node_id)
        self._sock.sendto(pkt, (self.multicast_group, self.port))

    def _send_beacon(self) -> None:
        if self._sock is None:
            return
        ts = now_ms()
        known = self.known_peers_for_beacon()
        pkt = encode_beacon(
            sender_id=self.node_id,
            timestamp_ms=ts,
            uptime_ms=self._uptime_ms(),
            theta=self.theta,
            known_peers=known,
        )
        self._sock.sendto(pkt, (self.multicast_group, self.port))

    def _listen_loop(self) -> None:
        """Receive packets and dispatch."""
        while self._running and self._sock:
            try:
                self._sock.settimeout(1.0)
                data, addr = self._sock.recvfrom(2048)
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                msg = decode_message(data)
            except Exception as exc:
                logger.debug("Decode error from %s: %s", addr, exc)
                continue

            sender = msg["sender_id"]
            if sender == self.node_id:
                continue  # ignore self

            if msg["type"] == MessageType.BEACON:
                self._handle_beacon(sender, addr, msg)
            elif msg["type"] == MessageType.LEAVE:
                self._handle_leave(sender, msg)
            else:
                # Other message types are handled by higher layers but we can log them
                logger.debug("Received %s from %d", msg["type"].name, sender)

    def _handle_beacon(self, sender: int, addr: tuple, msg: Dict) -> None:
        payload = msg["payload"]
        new_peer = False
        with self._lock:
            existing = self._peers.get(sender)
            if existing is None:
                new_peer = True
            self._peers[sender] = PeerInfo(
                node_id=sender,
                last_seen=time.monotonic(),
                uptime_ms=payload["uptime_ms"],
                theta=payload["theta"],
                addr=addr,
                known_peers=set(payload["known_peers"]),
            )
            # Merge detection: does this peer know nodes we don't?
            our_peers = set(self._peers.keys())
            foreign = payload["known_peers"] - our_peers - {self.node_id}

        if new_peer and self._on_peer_join:
            try:
                self._on_peer_join(self._peers[sender])
            except Exception:
                logger.exception("on_peer_join callback failed")

        if foreign and self._on_merge:
            try:
                self._on_merge(foreign)
            except Exception:
                logger.exception("on_merge callback failed")
            # Gossip pull: we don't know those nodes yet; our next BEACON will
            # include the sender so the foreign nodes can discover us back.

    def _handle_leave(self, sender: int, msg: Dict) -> None:
        node_id = msg["payload"]["node_id"]
        with self._lock:
            if node_id in self._peers:
                del self._peers[node_id]
        if self._on_peer_leave:
            try:
                self._on_peer_leave(node_id)
            except Exception:
                logger.exception("on_peer_leave callback failed")

    def _beacon_loop(self) -> None:
        while self._running and not self._shutdown_event.is_set():
            self._send_beacon()
            self._shutdown_event.wait(timeout=self.BEACON_INTERVAL)

    def _janitor_loop(self) -> None:
        """Remove peers that haven't been seen within PEER_TIMEOUT."""
        while self._running and not self._shutdown_event.is_set():
            self._shutdown_event.wait(timeout=self.PEER_TIMEOUT / 3)
            now = time.monotonic()
            timed_out = []
            with self._lock:
                for pid, info in list(self._peers.items()):
                    if now - info.last_seen > self.PEER_TIMEOUT:
                        timed_out.append(pid)
                        del self._peers[pid]
            for pid in timed_out:
                logger.info("Peer %d timed out", pid)
                if self._on_peer_leave:
                    try:
                        self._on_peer_leave(pid)
                    except Exception:
                        logger.exception("on_peer_leave callback failed")

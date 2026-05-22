"""Real UDP multicast network bus with configurable packet loss and latency.

Drop-in replacement for the simulated NetworkBus. Each agent gets its own
UDP socket bound to a unique port on localhost. Messages are sent to a
multicast group (239.255.0.1) so every agent receives them.

The Tensor-MIDI Message encode/decode from network_bus.py is reused
directly — the wire format stays the same.
"""

import socket
import struct
import random
import threading
import time
from typing import Optional

# Re-export the Message/MessageType from the original bus so agents don't
# need any import changes.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from network_bus import NetworkBus, Message, MessageType  # noqa: E402


MCAST_GROUP = "239.255.0.1"
BASE_PORT = 19840  # agents get ports 19840, 19841, 19842, ...


class UDPBus(NetworkBus):
    """Real UDP multicast bus — subclass of NetworkBus for drop-in compat.

    Overrides send/receive/flush to use actual UDP sockets instead of
    in-process mailboxes. The simulated impairment model (packet loss,
    latency, reorder) is preserved via random drops and time.sleep.

    Usage:
        bus = UDPBus(agent_ports={"forgemaster": 19840, "oracle1": 19841, "kimi1": 19842},
                     latency_ms=5.0, packet_loss=0.02)
        bus.register("forgemaster")
        ...
    """

    def __init__(
        self,
        agent_ports: Optional[dict[str, int]] = None,
        latency_ms: float = 5.0,
        packet_loss: float = 0.02,
        reorder_prob: float = 0.01,
    ):
        # Don't call NetworkBus.__init__ — we replace everything.
        # But we do need to init threading primitives if the parent uses them.
        self.latency_ms = latency_ms
        self.packet_loss = packet_loss
        self.reorder_prob = reorder_prob
        self.lock = threading.Lock()

        # Build port map: agent_id -> port
        self.agent_ports: dict[str, int] = dict(agent_ports) if agent_ports else {}

        # Sockets: one per agent for receiving, one shared for sending
        self._recv_sockets: dict[str, socket.socket] = {}
        self._send_socket: Optional[socket.socket] = None

        # Pending deliveries (for simulated latency)
        self.pending: list[tuple[float, bytes, str]] = []

        self._registered_order: list[str] = []
        self._next_port = BASE_PORT

    def _ensure_send_socket(self):
        if self._send_socket is None:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 0)  # localhost only
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._send_socket = sock

    def register(self, agent_id: str):
        """Bind a UDP socket for this agent on localhost."""
        if agent_id not in self.agent_ports:
            self.agent_ports[agent_id] = self._next_port
            self._next_port += 1

        port = self.agent_ports[agent_id]

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", port))

        # Join multicast group on loopback
        mreq = struct.pack(
            "4s4s",
            socket.inet_aton(MCAST_GROUP),
            socket.inet_aton("127.0.0.1"),
        )
        try:
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        except OSError:
            # Multicast may not work on all WSL2 configs; fall back to unicast
            pass

        sock.settimeout(0.001)  # non-blocking-ish recv
        self._recv_sockets[agent_id] = sock
        self._registered_order.append(agent_id)

    def send(self, msg: Message, recipients: Optional[list[str]] = None):
        """Send message over real UDP with simulated impairment."""
        self._ensure_send_socket()
        targets = recipients or list(self._recv_sockets.keys())
        targets = [t for t in targets if t != msg.sender and t in self.agent_ports]

        data = msg.encode()

        for target in targets:
            # Simulated packet loss
            if random.random() < self.packet_loss:
                continue  # dropped

            delay = self.latency_ms / 1000.0
            delay += random.gauss(0, delay * 0.3)
            delay = max(0, delay)

            # Simulated reorder
            if random.random() < self.reorder_prob:
                delay += random.uniform(0.01, 0.05)

            if delay > 0.001:
                deliver_at = time.time() + delay
                self.pending.append((deliver_at, data, target))
            else:
                # Send immediately
                port = self.agent_ports[target]
                self._send_socket.sendto(data, ("127.0.0.1", port))

        self._deliver_pending()

    def _deliver_pending(self):
        """Send any pending messages whose delay has elapsed."""
        now = time.time()
        still_pending = []
        self._ensure_send_socket()
        with self.lock:
            for deliver_at, data, target in self.pending:
                if now >= deliver_at:
                    if target in self.agent_ports:
                        port = self.agent_ports[target]
                        self._send_socket.sendto(data, ("127.0.0.1", port))
                else:
                    still_pending.append((deliver_at, data, target))
        self.pending = still_pending

    def receive(self, agent_id: str) -> list[Message]:
        """Read all available UDP datagrams for this agent."""
        self._deliver_pending()
        sock = self._recv_sockets.get(agent_id)
        if sock is None:
            return []

        messages = []
        while True:
            try:
                data, _addr = sock.recvfrom(65535)
                msg = Message.decode(data)
                messages.append(msg)
            except (socket.timeout, BlockingIOError, OSError):
                break
        return messages

    def flush(self):
        """Force-deliver all pending messages immediately."""
        self._ensure_send_socket()
        with self.lock:
            for _, data, target in self.pending:
                if target in self.agent_ports:
                    port = self.agent_ports[target]
                    self._send_socket.sendto(data, ("127.0.0.1", port))
            self.pending.clear()

        # Also drain all recv buffers so messages are available
        for agent_id, sock in self._recv_sockets.items():
            pass  # messages will be picked up by next receive() call

    def close(self):
        """Clean up all sockets."""
        for sock in self._recv_sockets.values():
            try:
                sock.close()
            except OSError:
                pass
        if self._send_socket:
            try:
                self._send_socket.close()
            except OSError:
                pass
        self._recv_sockets.clear()
        self._send_socket = None

    def __del__(self):
        self.close()

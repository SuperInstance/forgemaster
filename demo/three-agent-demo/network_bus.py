"""Simulated UDP network bus with latency, packet loss, and reorder."""

import random
import time
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional


class MessageType(Enum):
    TICK = auto()
    DRIFT_REPORT = auto()
    CADENCE_CALL = auto()
    CORRECTION = auto()
    SUNSET = auto()
    INHERIT = auto()
    CONSTRAINT_VIOLATION = auto()
    HOLOMONY_REPORT = auto()
    NERVE_METRIC = auto()
    TENSOR_MIDI = auto()


@dataclass
class Message:
    msg_type: MessageType
    sender: str
    payload: dict = field(default_factory=dict)
    tick: int = 0
    ts: float = field(default_factory=time.time)

    def encode(self) -> bytes:
        """Tensor-MIDI inspired encoding: type|sender|tick|key=value;..."""
        parts = [self.msg_type.name, self.sender, str(self.tick)]
        kv = ";".join(f"{k}={v}" for k, v in self.payload.items())
        parts.append(kv)
        return "|".join(parts).encode("utf-8")

    @classmethod
    def decode(cls, data: bytes) -> "Message":
        """Decode Tensor-MIDI encoding back to Message."""
        parts = data.decode("utf-8").split("|", 3)
        msg_type = MessageType[parts[0]]
        sender = parts[1]
        tick = int(parts[2])
        payload = {}
        if len(parts) > 3 and parts[3]:
            for pair in parts[3].split(";"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    payload[k] = v
        return cls(msg_type=msg_type, sender=sender, payload=payload, tick=tick)


class NetworkBus:
    """Simulated UDP bus with configurable impairment."""

    def __init__(
        self,
        latency_ms: float = 5.0,
        packet_loss: float = 0.02,
        reorder_prob: float = 0.01,
    ):
        self.latency_ms = latency_ms
        self.packet_loss = packet_loss
        self.reorder_prob = reorder_prob
        self.mailboxes: dict[str, deque[Message]] = defaultdict(deque)
        self.pending: list[tuple[float, Message, str]] = []
        self.lock = threading.Lock()
        self._tick_counter = 0

    def register(self, agent_id: str):
        self.mailboxes[agent_id] = deque()

    def send(self, msg: Message, recipients: Optional[list[str]] = None):
        """Send message to recipients (or broadcast if None)."""
        targets = recipients or list(self.mailboxes.keys())
        targets = [t for t in targets if t != msg.sender]

        for target in targets:
            if random.random() < self.packet_loss:
                continue  # dropped

            delay = self.latency_ms / 1000.0
            # Add jitter
            delay += random.gauss(0, delay * 0.3)
            deliver_at = time.time() + max(0, delay)

            # Reorder: sometimes delay extra
            if random.random() < self.reorder_prob:
                deliver_at += random.uniform(0.01, 0.05)

            self.pending.append((deliver_at, msg, target))

        # Deliver ready messages
        self._deliver()

    def _deliver(self):
        now = time.time()
        still_pending = []
        with self.lock:
            for deliver_at, msg, target in self.pending:
                if now >= deliver_at:
                    self.mailboxes[target].append(msg)
                else:
                    still_pending.append((deliver_at, msg, target))
        self.pending = still_pending

    def receive(self, agent_id: str) -> list[Message]:
        """Get all pending messages for an agent."""
        self._deliver()
        with self.lock:
            msgs = list(self.mailboxes[agent_id])
            self.mailboxes[agent_id].clear()
        return msgs

    def flush(self):
        """Force-deliver all pending messages."""
        with self.lock:
            for _, msg, target in self.pending:
                self.mailboxes[target].append(msg)
            self.pending.clear()

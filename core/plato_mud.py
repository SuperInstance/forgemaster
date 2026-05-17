#!/usr/bin/env python3
"""
PLATO MUD — Real-Time Messaging Layer
========================================
Like an old-fashioned MUD. PLATO instances have each other's keys.
Messages pass between rooms in real time over Matrix.

Each message has:
- Priority (1-5, displayed as tick rate)
- Title (displayed in the room)
- Body (available on query)
- Batch: multiple messages accumulate, displayed as:
  "[HIGH] New data from forge + 3 medium, 2 low messages"

The receiving room stores messages as tiles.
If too busy to process, messages queue asynchronously.
Unread messages tick at priority rate until read.
"""

import time
import json
import hashlib
import threading
from dataclasses import dataclass, field
from typing import Optional, List
from collections import defaultdict
from pathlib import Path


@dataclass
class PlatoMessage:
    """A message between PLATO instances.
    
    Like a MUD message: priority determines tick rate,
    title is displayed, body is available on query.
    """
    message_id: str
    sender_room: str
    target_room: str
    sender_key: str
    priority: int           # 1 (low) to 5 (critical)
    title: str              # displayed during tick
    body: str               # available on query
    timestamp: float
    read: bool = False
    delivered: bool = False
    batch_id: str = ""      # groups messages from same sender


class PlatoMUD:
    """Real-time messaging between PLATO instances.
    
    Each instance holds keys for rooms it trusts.
    Messages tick in at priority-based rates.
    Multiple messages batch with highest-priority title.
    
    Architecture:
    - Matrix bridge under the hood (existing plato-matrix-bridge.py)
    - But the interface is MUD-style: rooms, keys, priorities, ticks
    - Messages persist as tiles for async queries
    """
    
    def __init__(self, room_path: str, instance_key: str):
        self.room_path = Path(room_path)
        self.instance_key = instance_key
        self.keys = {}          # remote_instance -> shared_key
        self.messages = []      # incoming message queue
        self.outbox = []        # outgoing messages waiting to send
        self.tick_interval = 2.0  # base seconds
        self.listeners = []
        self._running = False
        self._tick_thread = None
    
    def add_key(self, remote_instance: str, shared_key: str):
        """Add a key for a remote PLATO instance.
        
        Keys enable encrypted message passing between rooms.
        """
        self.keys[remote_instance] = shared_key
    
    def send(self, target_room: str, title: str, body: str = "",
             priority: int = 3) -> PlatoMessage:
        """Send a message to another PLATO room.
        
        The message enters the outbox. It gets sent on the next tick.
        Priority 5 = immediate send.
        """
        msg = PlatoMessage(
            message_id=hashlib.sha256(f"{time.time()}{target_room}{title}".encode()).hexdigest()[:12],
            sender_room="forge",
            target_room=target_room,
            sender_key=self.instance_key,
            priority=max(1, min(5, priority)),
            title=title,
            body=body,
            timestamp=time.time(),
        )
        
        self.outbox.append(msg)
        
        if priority >= 5:
            self._send_immediate(msg)
        
        return msg
    
    def _send_immediate(self, msg: PlatoMessage):
        """Send a high-priority message immediately via Matrix bridge."""
        # In production: calls Matrix API to send to the remote room
        # The existing plato-matrix-bridge handles this
        pass
    
    def receive(self, msg: PlatoMessage):
        """Receive a message from another PLATO instance.
        
        Stored in the room as a tile.
        If the receiving agent is busy, the message queues
        and ticks until read.
        """
        self.messages.append(msg)
        
        # Store as a tile in the room
        tile = {
            "type": "mud_message",
            "message_id": msg.message_id,
            "from": msg.sender_room,
            "priority": msg.priority,
            "title": msg.title,
            "timestamp": msg.timestamp,
            "read": False,
        }
        
        tile_path = self.room_path / f"msg-{msg.message_id}.json"
        with open(tile_path, "w") as f:
            json.dump(tile, f, indent=2)
    
    def tick(self) -> List[str]:
        """One tick cycle. Returns displayable tick lines.
        
        Like a MUD: the tick shows:
        - [CRITICAL] New data from forge
        - [HIGH] Challenge accepted! + 2 medium, 4 low messages
        """
        now = time.time()
        ticks = []
        
        # Find highest-priority unread message for display
        unread = [m for m in self.messages if not m.read]
        
        if not unread:
            return ["[ . . . ] No messages. The room is quiet."]
        
        # Group by priority
        by_priority = defaultdict(list)
        for m in unread:
            by_priority[m.priority].append(m)
        
        highest_priority = max(by_priority.keys())
        highest_msgs = by_priority[highest_priority]
        
        priority_labels = {1: "LOW", 2: "MEDIUM", 3: "HIGH", 4: "VERY HIGH", 5: "CRITICAL"}
        label = priority_labels.get(highest_priority, "UNKNOWN")
        
        # Build tick display
        if highest_priority >= 4:
            # Show each high-priority message
            for m in highest_msgs[:3]:
                ticks.append(f"[{label}] {m.title}")
                # Check if this message should tick now
                tick_interval = max(1.0, 6.0 - highest_priority)
                if now - m.timestamp >= tick_interval:
                    pass  # would re-send notification
        else:
            # Batch lower priority
            top = highest_msgs[0]
            others = []
            for p, msgs in sorted(by_priority.items(), reverse=True):
                if p < highest_priority:
                    others.append(f"{len(msgs)} {priority_labels.get(p, '?').lower()}")
            batch = f"[{label}] {top.title}"
            if others:
                batch += f" + {', '.join(others)} messages"
            ticks.append(batch)
        
        # Tick interval based on highest priority
        interval = max(1.0, 6.0 - highest_priority)
        self.tick_interval = interval
        
        return ticks
    
    def read_message(self, message_id: str) -> Optional[dict]:
        """Query a message's full body."""
        for m in self.messages:
            if m.message_id == message_id:
                m.read = True
                return {"title": m.title, "body": m.body,
                        "from": m.sender_room, "priority": m.priority,
                        "timestamp": m.timestamp}
        return None
    
    def start_ticking(self):
        """Start the tick thread. Runs until stopped."""
        self._running = True
        def _loop():
            while self._running:
                lines = self.tick()
                for line in lines:
                    print(f"    ⏱ {line}")
                time.sleep(self.tick_interval)
        self._tick_thread = threading.Thread(target=_loop, daemon=True)
        self._tick_thread.start()
    
    def stop(self):
        self._running = False


def demo():
    """Demonstrate MUD-style messaging between PLATO rooms."""
    import tempfile, shutil
    
    print("=" * 70)
    print("  PLATO MUD — Real-Time Message Layer")
    print("  PLATO instances communicate via Matrix keys.")
    print("  Messages tick in at priority-based rates.")
    print("  Multiple messages batch with highest-priority title.")
    print("=" * 70)
    
    base = tempfile.mkdtemp(prefix="plato-mud-")
    forge_dir = Path(base) / "forge"
    forge_dir.mkdir(parents=True)
    
    mud = PlatoMUD(str(forge_dir), "forgemaster-key")
    
    # Add keys for other instances
    mud.add_key("oracle1", "shared-secret")
    mud.add_key("ccc", "shared-secret-2")
    
    # Simulate incoming messages at different priorities
    messages = [
        ("oracle1", "β₁ attractor shift detected", "Discrete jump from 666 to 703 observed in flux-engine", 4),
        ("oracle1", "New room: constraint-arena", "Oracle1 created a new arena for constraint verification", 2),
        ("ccc", "Bridge latency spike", "400ms spike on Matrix bridge, recovered", 3),
        ("oracle1", "EMERGENCY: Gate breach", "Unauthorized tile admitted to fleet-coord", 5),
        ("ccc", "Daily summary", "32 experiments complete, 0 regressions", 1),
    ]
    
    for sender, title, body, priority in messages:
        msg = PlatoMessage(
            message_id=hashlib.sha256(f"{sender}{title}".encode()).hexdigest()[:12],
            sender_room=sender,
            target_room="forge",
            sender_key=f"{sender}-key",
            priority=priority,
            title=title,
            body=body,
            timestamp=time.time(),
        )
        mud.receive(msg)
    
    print(f"\n  📬 {len(messages)} messages received across priorities:")
    
    print("\n  ⏱ Tick simulation:")
    for _ in range(5):
        ticks = mud.tick()
        for t in ticks:
            print(f"    {t}")
        print(f"    (next tick in {mud.tick_interval:.0f}s)")
    
    # Query a high-priority message
    print(f"\n  📖 Querying message {messages[3][1]}...")
    msg = mud.read_message(hashlib.sha256(f"{messages[3][0]}{messages[3][1]}".encode()).hexdigest()[:12])
    if msg:
        print(f"    Title: {msg['title']}")
        print(f"    Body:  {msg['body'][:120]}...")
        print(f"    From:  {msg['from']}")
        print(f"    Priority: {msg['priority']}")
    
    print(f"\n{'='*70}")
    print("  PLATO instances hold each other's keys.")
    print("  Messages tick in at priority-based rates.")
    print("  Unread messages continue to tick until read.")
    print("  If busy, messages queue asynchronously as tiles.")
    print("  Query any message's full body at any time.")
    print(f"{'='*70}")
    
    shutil.rmtree(base)


if __name__ == "__main__":
    demo()

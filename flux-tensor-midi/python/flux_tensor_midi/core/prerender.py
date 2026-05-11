"""
Pre-render forward buffer for FLUX-Tensor-MIDI rooms.

Each room plans ahead like a Rubik's cube speed-solver:
  1. Inspect current state (listen)
  2. Plan the sequence (pre-render)
  3. Execute committed beats (play)
  4. Overlap: plan next sequence during execution

Three zones:
  - Committed: locked, executing now (1-2 beats)
  - Tentative: planned, adjustable (2-4 beats)
  - Sketch: rough, scrappable (2-8 beats)
"""

import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Callable, Dict, List, Optional


class Zone(IntEnum):
    COMMITTED = 0
    TENTATIVE = 1
    SKETCH = 2


@dataclass
class PreRenderedBeat:
    """A single pre-rendered beat in the forward buffer."""
    beat: float
    zone: Zone
    tile: Any  # The pre-rendered content
    confidence: float = 1.0  # How confident we are (1.0 = locked, 0.0 = wild guess)
    created_at: float = field(default_factory=time.time)
    adjusted: int = 0  # How many times this was adjusted
    
    def is_locked(self) -> bool:
        return self.zone == Zone.COMMITTED
    
    def is_adjustable(self) -> bool:
        return self.zone in (Zone.TENTATIVE, Zone.SKETCH)


class PreRenderBuffer:
    """
    A room's forward-looking script buffer.
    
    Like a Rubik's cube speed-solver, the room:
    - Plans several beats ahead while executing current beats
    - Commits to near-term beats (can't change)
    - Keeps far-term beats tentative (can adjust based on new info)
    - Sketches very-far-term beats (can scrap entirely)
    """
    
    def __init__(
        self,
        room_id: str,
        depth: int = 6,
        commit_window: int = 1,
        tentative_window: int = 3,
        sketch_window: int = 2,
    ):
        self.room_id = room_id
        self.depth = depth
        self.commit_window = commit_window
        self.tentative_window = tentative_window
        self.sketch_window = sketch_window
        
        # The three zones
        self.committed: Dict[float, PreRenderedBeat] = {}
        self.tentative: Dict[float, PreRenderedBeat] = {}
        self.sketch: Dict[float, PreRenderedBeat] = {}
        
        # Planning function (injected by the room)
        self.plan_fn: Optional[Callable] = None
        self.render_fn: Optional[Callable] = None
        
        # Statistics
        self.total_planned = 0
        self.total_adjusted = 0
        self.total_scrapped = 0
        self.cache_hits = 0
        self.cache_misses = 0
    
    def advance(self, current_beat: float):
        """
        Advance the buffer forward. Called every tick.
        
        Promotes: sketch → tentative → committed → played (removed)
        Fills: new sketch beats at the far end
        """
        # 1. Remove played committed beats
        played = [b for b in self.committed if b < current_beat]
        for b in played:
            del self.committed[b]
        
        # 2. Promote tentative → committed (entering commit window)
        commit_threshold = current_beat + self.commit_window
        entering = [b for b in self.tentative if b <= commit_threshold]
        for b in sorted(entering):
            beat = self.tentative.pop(b)
            beat.zone = Zone.COMMITTED
            beat.confidence = 1.0
            self.committed[b] = beat
        
        # 3. Promote sketch → tentative (entering tentative window)
        tentative_threshold = current_beat + self.commit_window + self.tentative_window
        entering = [b for b in self.sketch if b <= tentative_threshold]
        for b in sorted(entering):
            sketch = self.sketch.pop(b)
            # Render the sketch into a proper tile
            rendered_tile = self._render(sketch.tile) if self.render_fn else sketch.tile
            self.tentative[b] = PreRenderedBeat(
                beat=b,
                zone=Zone.TENTATIVE,
                tile=rendered_tile,
                confidence=0.7,
            )
            self.total_planned += 1
        
        # 4. Fill sketch zone with new plans
        sketch_start = current_beat + self.commit_window + self.tentative_window + 1
        sketch_end = current_beat + self.depth
        for b in range(int(sketch_start), int(sketch_end) + 1):
            if b not in self.committed and b not in self.tentative and b not in self.sketch:
                plan = self._plan(b) if self.plan_fn else {"beat": b, "content": None}
                self.sketch[b] = PreRenderedBeat(
                    beat=b,
                    zone=Zone.SKETCH,
                    tile=plan,
                    confidence=0.3,
                )
                self.total_planned += 1
    
    def get_beat(self, beat: float) -> Optional[PreRenderedBeat]:
        """Get a pre-rendered beat (cache lookup)."""
        if beat in self.committed:
            self.cache_hits += 1
            return self.committed[beat]
        if beat in self.tentative:
            self.cache_hits += 1
            return self.tentative[beat]
        if beat in self.sketch:
            self.cache_hits += 1
            return self.sketch[beat]
        self.cache_misses += 1
        return None
    
    def adjust(self, beat: float, new_tile: Any) -> bool:
        """Adjust a tentative or sketch beat. Returns False if beat is committed."""
        if beat in self.committed:
            return False  # Can't adjust committed beats
        
        if beat in self.tentative:
            self.tentative[beat].tile = new_tile
            self.tentative[beat].adjusted += 1
            self.total_adjusted += 1
            return True
        
        if beat in self.sketch:
            self.sketch[beat].tile = new_tile
            self.sketch[beat].adjusted += 1
            self.total_adjusted += 1
            return True
        
        return False
    
    def react_to_signal(self, signal_beat: float, signal_type: str, signal_data: Any = None):
        """
        React to a side-channel signal by adjusting the forward buffer.
        
        nod: "I'm ready" → confirm plans, maybe commit further
        smile: "that was good" → extend commit window, increase confidence
        frown: "something's off" → drop tentative plans, re-plan from signal
        breath: "about to act" → prepare for change, pause sketch zone
        """
        if signal_type == "nod":
            # Confirm: promote one more sketch → tentative
            if self.sketch:
                next_beat = min(self.sketch.keys())
                sketch = self.sketch.pop(next_beat)
                self.tentative[next_beat] = PreRenderedBeat(
                    beat=next_beat,
                    zone=Zone.TENTATIVE,
                    tile=self._render(sketch.tile) if self.render_fn else sketch.tile,
                    confidence=0.8,
                )
        
        elif signal_type == "smile":
            # Extend confidence on tentative beats
            for b in self.tentative:
                self.tentative[b].confidence = min(1.0, self.tentative[b].confidence + 0.1)
        
        elif signal_type == "frown":
            # Drop and re-plan tentative beats after the signal
            to_drop = [b for b in self.tentative if b > signal_beat]
            for b in to_drop:
                self.total_scrapped += 1
                new_plan = self._plan(b) if self.plan_fn else {"beat": b, "content": "replanned"}
                self.sketch[b] = PreRenderedBeat(
                    beat=b, zone=Zone.SKETCH, tile=new_plan, confidence=0.2
                )
                del self.tentative[b]
        
        elif signal_type == "breath":
            # Pause sketch planning — keep what we have but don't extend
            pass  # No new sketches until we see what happens
    
    def _plan(self, beat: float) -> Any:
        """Generate a rough plan for a future beat."""
        if self.plan_fn:
            return self.plan_fn(beat)
        return {"beat": beat, "room": self.room_id, "status": "planned"}
    
    def _render(self, sketch: Any) -> Any:
        """Render a sketch into a proper tile."""
        if self.render_fn:
            return self.render_fn(sketch)
        return sketch
    
    def stats(self) -> dict:
        """Buffer statistics."""
        return {
            "room_id": self.room_id,
            "committed": len(self.committed),
            "tentative": len(self.tentative),
            "sketch": len(self.sketch),
            "total_planned": self.total_planned,
            "total_adjusted": self.total_adjusted,
            "total_scrapped": self.total_scrapped,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": self.cache_hits / max(1, self.cache_hits + self.cache_misses),
        }
    
    def visualize(self, current_beat: float, width: int = 60) -> str:
        """ASCII visualization of the forward buffer."""
        lines = []
        lines.append(f"Pre-Render Buffer: {self.room_id} (current beat: {current_beat:.0f})")
        lines.append("─" * width)
        
        for beat in range(int(current_beat), int(current_beat + self.depth) + 1):
            b = float(beat)
            if b in self.committed:
                zone = "COMMITTED"
                tile = str(self.committed[b].tile)[:20]
                conf = "█" * 10
            elif b in self.tentative:
                zone = "TENTATIVE"
                tile = str(self.tentative[b].tile)[:20]
                c = int(self.tentative[b].confidence * 10)
                conf = "█" * c + "░" * (10 - c)
            elif b in self.sketch:
                zone = "SKETCH   "
                tile = str(self.sketch[b].tile)[:20]
                c = int(self.sketch[b].confidence * 10)
                conf = "█" * c + "░" * (10 - c)
            else:
                zone = "EMPTY    "
                tile = ""
                conf = "░" * 10
            
            now_marker = "→ " if beat == int(current_beat) else "  "
            lines.append(f"{now_marker}Beat {beat:3d} │ {zone} │ {conf} │ {tile}")
        
        lines.append("─" * width)
        s = self.stats()
        lines.append(f"Hit rate: {s['hit_rate']:.0%} | Adjusted: {s['total_adjusted']} | Scrapped: {s['total_scrapped']}")
        return "\n".join(lines)


# ── Demo ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  🧩 PRE-RENDER FORWARD BUFFER — Rubik's Cube Model")
    print("=" * 60)
    print()
    
    # Create a buffer for a game NPC
    def plan_dialogue(beat):
        """Plan what the NPC might say at a future beat."""
        lines = [
            "greeting", "question", "response", "idle",
            "greeting", "question", "response", "idle",
            "farewell", "idle", "idle", "idle",
        ]
        return {"beat": beat, "dialogue": lines[int(beat) % len(lines)]}
    
    def render_dialogue(sketch):
        """Render a dialogue sketch into a concrete line."""
        dialogue_map = {
            "greeting": "Hello there!",
            "question": "What brings you here?",
            "response": "Interesting...",
            "idle": "...",
            "farewell": "Safe travels!",
        }
        return {
            "beat": sketch["beat"],
            "line": dialogue_map.get(sketch.get("dialogue", "idle"), "..."),
        }
    
    buffer = PreRenderBuffer(
        room_id="npc_guard",
        depth=8,
        commit_window=1,
        tentative_window=3,
        sketch_window=4,
    )
    buffer.plan_fn = plan_dialogue
    buffer.render_fn = render_dialogue
    
    # Simulate 12 beats
    for beat in range(12):
        print(f"\n{'='*60}")
        print(f"  BEAT {beat}")
        print(f"{'='*60}")
        
        buffer.advance(float(beat))
        print(buffer.visualize(float(beat)))
        
        # Simulate side-channel signals
        if beat == 4:
            print("\n  📨 Signal: FROWN from player (unexpected question)")
            buffer.react_to_signal(float(beat), "frown", {"type": "interruption"})
            print("  → Dropped tentative plans, re-planning...")
        
        if beat == 7:
            print("\n  📨 Signal: NOD from npc_bard (your turn)")
            buffer.react_to_signal(float(beat), "nod")
            print("  → Promoted one sketch → tentative")
        
        if beat == 10:
            print("\n  📨 Signal: SMILE from player (good dialogue)")
            buffer.react_to_signal(float(beat), "smile")
            print("  → Boosted confidence on tentative beats")
    
    print(f"\n{'='*60}")
    print(f"  FINAL STATS")
    print(f"{'='*60}")
    stats = buffer.stats()
    for k, v in stats.items():
        print(f"  {k:20} = {v}")

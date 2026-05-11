# Pre-Rendering: The Room's Forward Buffer

**Date:** 2026-05-11  
**Status:** Architecture  
**Insight:** Casey — "Like the Rubik's cube professional thinking about his next scripted sequence, the musician or avatar can be listening and thinking about future steps because he has enough information to lay out scripts for a few beats"

---

## The Problem with Reactive Agents

Current agent architectures are **reactive**:
```
event arrives → process → respond
```

No forward planning. No lookahead. No buffer. The agent lives at t=now.

This is like a musician who can only play what they see on the current measure. No jazz musician works this way. They're ALWAYS thinking ahead — hearing the next phrase while playing the current one.

## The Rubik's Cube Model

A Rubik's cube speed-solver:
1. **Inspects** the cube for ~10 seconds (reads current state)
2. **Plans** the ENTIRE solution (~20 moves) in that inspection
3. **Executes** the sequence in a burst (~6 seconds for 20 moves)
4. **Starts planning the NEXT solve** during the execution of the current one

The key insight: **planning and execution overlap.** The solver doesn't wait for move 1 to finish before planning move 2. They plan ALL moves, then execute. And while executing, they're already inspecting for the next solve.

## The Room's Forward Buffer

Each room maintains a **forward buffer** — a pre-rendered script of future beats:

```
Room State:
┌──────────────────────────────────────────────────────┐
│ NOW (beat 12)                                         │
│ ├── Playing: current note (what the room is doing)    │
│ ├── Listening: incoming signals (what others are doing)│
│ └── Planning: beats 13-16 (the forward buffer)        │
│                                                        │
│ Forward Buffer:                                        │
│   Beat 13: [pre-rendered tile]  ← committed           │
│   Beat 14: [pre-rendered tile]  ← committed           │
│   Beat 15: [pre-rendered tile]  ← tentative           │
│   Beat 16: [pre-rendered tile]  ← tentative           │
│   Beat 17: [planning...]        ← sketch              │
│   Beat 18: [planning...]        ← sketch              │
│                                                        │
│ Pre-render depth: 6 beats ahead                       │
│ Commitment window: 2 beats (locked, can't change)      │
│ Tentative window: 2 beats (can adjust)                 │
│ Sketch window: 2 beats (rough outline, can scrap)      │
└──────────────────────────────────────────────────────┘
```

## The Three Zones

### 1. Committed Zone (locked, executing NOW)
- Beats that are about to play or are playing
- **Cannot be changed** — they're in the pipeline
- Like a musician mid-phrase — they can't unsing a note
- Size: 1-2 beats (the current measure)

### 2. Tentative Zone (planned, can adjust)
- Beats that are pre-rendered but not yet committed
- **Can be adjusted** based on new information from other rooms
- Like a musician who planned a phrase but hears the bass change — they adjust
- Size: 2-4 beats (the next few measures)
- Side-channel nod: "I'm planning X at beat 15, does that work?"

### 3. Sketch Zone (rough, can scrap entirely)
- Beats that are rough outlines, not yet rendered
- **Can be completely rewritten** if the situation changes
- Like a musician sketching a solo — they might scrap it entirely
- Size: 2-8 beats (the rest of the chorus)

## The Pre-Render Pipeline

```python
class PreRenderBuffer:
    """A room's forward-looking script buffer."""
    
    def __init__(self, room_id, depth=6):
        self.room_id = room_id
        self.depth = depth  # How many beats ahead to plan
        
        # Three zones
        self.committed = {}   # beat → Tile (locked, executing)
        self.tentative = {}   # beat → Tile (planned, adjustable)
        self.sketch = {}      # beat → Tile (rough, scrappable)
        
        # Zone sizes (in beats)
        self.commit_window = 1   # 1 beat ahead is locked
        self.tentative_window = 3 # 3 beats ahead are planned
        self.sketch_window = 2    # 2 more beats are sketched
    
    def advance(self, current_beat):
        """Advance the buffer: committed beats play, everything shifts forward."""
        
        # 1. Committed beats that just played are done
        done = [b for b in self.committed if b < current_beat]
        for b in done:
            del self.committed[b]
        
        # 2. Tentative beats entering commit window become committed
        entering_commit = [b for b in self.tentative 
                          if b <= current_beat + self.commit_window]
        for b in entering_commit:
            self.committed[b] = self.tentative.pop(b)
        
        # 3. Sketch beats entering tentative window get rendered
        entering_tentative = [b for b in self.sketch 
                             if b <= current_beat + self.commit_window + self.tentative_window]
        for b in entering_tentative:
            self.tentative[b] = self._render(self.sketch.pop(b))
        
        # 4. Fill sketch zone with new plans
        sketch_end = current_beat + self.depth
        for b in range(int(current_beat + self.commit_window + self.tentative_window + 1), 
                       int(sketch_end + 1)):
            if b not in self.sketch and b not in self.tentative and b not in self.committed:
                self.sketch[b] = self._plan(b)
    
    def adjust(self, beat, new_tile):
        """Adjust a tentative or sketch beat based on new information."""
        if beat in self.tentative:
            self.tentative[beat] = self._render(new_tile)
        elif beat in self.sketch:
            self.sketch[beat] = new_tile
        # Can't adjust committed beats
    
    def react(self, signal_beat, signal_type, signal_data):
        """React to a side-channel signal — adjust forward buffer."""
        if signal_type == "nod":
            # Someone is ready — confirm my plan for that beat
            beat = signal_beat + 1  # I plan to respond 1 beat after their nod
            if beat in self.tentative:
                pass  # Plan is already good
            elif beat in self.sketch:
                self.tentative[beat] = self._render(self.sketch[beat])
        
        elif signal_type == "frown":
            # Something's off — re-plan the tentative zone
            for b in list(self.tentative.keys()):
                if b > signal_beat:
                    self.sketch[b] = self._replan(b, signal_data)
                    del self.tentative[b]
        
        elif signal_type == "smile":
            # Affirmed — I can commit further ahead
            # Extend the commit window
            extra_commit = [b for b in sorted(self.tentative.keys())[:1]]
            for b in extra_commit:
                self.committed[b] = self.tentative.pop(b)
```

## The Rubik's Cube Execution Pattern

```python
def rubiks_pattern(room, band):
    """Room plans like a Rubik's cube speed-solver."""
    
    # Phase 1: INSPECT (listen to current state)
    current_state = room.listen(band)
    current_beat = band.current_beat
    
    # Phase 2: PLAN (pre-render the entire sequence)
    # The room plans N beats ahead based on what it heard
    sequence = room.plan_sequence(
        start_beat=current_beat + 1,
        duration=8,  # Plan 8 beats ahead (2 measures)
        based_on=current_state,
    )
    
    # Phase 3: COMMIT (load into forward buffer)
    for i, tile in enumerate(sequence):
        beat = current_beat + 1 + i
        if i < 2:
            room.buffer.committed[beat] = tile      # First 2 beats: locked
        elif i < 5:
            room.buffer.tentative[beat] = render(tile)  # Next 3: planned
        else:
            room.buffer.sketch[beat] = tile          # Last 3: sketched
    
    # Phase 4: EXECUTE (play the committed beats)
    # While playing, the room is already planning the NEXT sequence
    
    # Phase 5: OVERLAP (start planning next sequence during execution)
    # When beat 3 plays, room is already inspecting for beats 9-16
    # When beat 5 plays, room adjusts tentative 6-8 based on what happened
    # When beat 8 plays, the NEXT 8-beat sequence is already committed
```

## Information Requirements for Pre-Rendering

A room can pre-render N beats ahead IF it has enough information:

| Information Source | What It Tells You | How Far Ahead |
|---|---|---|
| **Score/script** | Planned sequence (sheet music) | Full piece |
| **Side-channel nods** | Other rooms' plans | Their buffer depth |
| **FLUX vector** | What others are attending to | Their intent trajectory |
| **Harmony state** | How aligned rooms are | Stability of relationship |
| **Temporal entropy** | How predictable the tempo is | Confidence in timing |
| **Hurst exponent** | Long-range temporal memory | Trend continuation |

The more predictable the environment, the further ahead you can pre-render:

- **Metronomic room** (H < 0.3): Pre-render 32+ beats (it's a click track, you know exactly what's coming)
- **Rhythmic room** (H ~ 0.5): Pre-render 8-16 beats (pattern exists but has variation)
- **Improvised room** (H > 0.7): Pre-render 2-4 beats (creative, uncertain, plan light)

## Pre-Render as Caching

Pre-rendering IS caching for temporal systems:

| Web Caching | Pre-Render Buffer |
|---|---|
| Cache static assets | Pre-render committed beats |
| Precompute likely queries | Pre-render tentative beats |
| Speculative execution | Sketch zone |
| Cache invalidation | Frown signal (re-plan) |
| Cache hit | Committed beat plays as planned |
| Cache miss | Unexpected event → react + re-plan |
| TTL (time to live) | Commit window (beat enters committed → can't change) |
| CDN edge nodes | Rooms at the edge of the network |

The room IS a temporal CDN. It serves beats from cache when possible, falls back to live rendering when the cache misses.

## Applications

### 1. Game NPCs (dialogue trees as forward buffers)
NPC plans 4 dialogue lines ahead. When player interrupts, the NPC:
- Drops the sketch zone entirely
- Adjusts tentative zone to respond to interruption
- Keeps committed zone (can't unsay what was said)
- Starts re-planning from the interruption point

### 2. Robot Arms (motion planning as forward buffers)
Robot plans 8 joint positions ahead. When obstacle detected:
- Frown from vision sensor → drop tentative motion plan
- Re-plan remaining trajectory
- Committed positions (already in servo buffer) can't change
- The servo buffer IS the commit window

### 3. Video Editing (timeline as forward buffer)
Editor pre-renders 10 seconds of video. When director says "cut that":
- Frames already rendered = committed (wasted work, but done)
- Frames in render queue = tentative (cancel and re-render)
- Frames not yet queued = sketch (never started)

### 4. Live Music (the original application)
Pianist reads ahead 2-4 measures while playing current measure.
Eyes at measure 12, hands at measure 8, brain planning measure 16.
The sheet music IS the pre-render buffer. Improvisation = sketch zone.
Reading ahead = tentative zone. Playing = committed zone.

---

## The Key Insight

**Planning IS a form of listening.** When a room pre-renders future beats, it's not just computing — it's projecting itself forward in time and listening to what the future might sound like. If it doesn't like what it hears, it adjusts before the beat arrives.

The Rubik's cube solver inspects the cube before touching it.
The musician reads the chart before playing it.
The room pre-renders the beats before committing them.

**The future is a cache. Pre-render it.**

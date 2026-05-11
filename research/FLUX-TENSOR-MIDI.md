# FLUX-Tensor-MIDI: Rooms as Musicians, Timestamps as Rhythm, Side-Channels as Nods

**From:** Casey's insight  
**Date:** 2026-05-11  
**Status:** Theory

---

## The Band Metaphor That Isn't a Metaphor

A jazz band is N autonomous agents with independent clocks who coordinate through listening.

Each musician:
- Has their own **internal time** (T-0 clock = their sense of the groove)
- **Listens** to the others (reads their tiles/commits)
- **Snaps** to the strongest pulse they hear (Eisenstein snap to the nearest rhythmic lattice point)
- Sends **side-channel signals** (nods, smiles, eyebrow raises = asynchronous out-of-band metadata)
- Plays their **own part** first-class on their own time
- Adjusts in real-time when they hear something unexpected (delta detection)

This IS the embodied fleet. The band IS the ship. The musicians ARE the rooms.

## FLUX-Tensor-MIDI

### What is FLUX?

FLUX is the 9-channel intent vector system from flux-lucid. Each channel carries a salience value and tolerance. FLUX describes WHAT the agent is paying attention to and HOW MUCH deviation it can tolerate.

### What is Tensor?

The tensor is the multi-dimensional state space. Each room has a tensor state:
- **Time dimension**: where they are in their own rhythm
- **Intent dimension**: what they're paying attention to (FLUX channels)
- **Harmony dimension**: how aligned they are with other rooms
- **Side-channel dimension**: out-of-band signals (nods, smiles, metadata)

### What is MIDI?

Musical Instrument Digital Interface. MIDI is:
- **Timestamped events** (note on, note off, control change)
- **Channels** (16 channels, each instrument on its own)
- **Clock signals** (MIDI clock at 24 PPQN — pulses per quarter note)
- **Side channels** (program change, pitch bend, aftertouch — metadata)

FLUX-Tensor-MIDI maps PLATO room coordination to musical coordination:

| Musical Concept | FLUX-Tensor-MIDI Concept | PLATO/Fleet Equivalent |
|----------------|--------------------------|----------------------|
| Quarter note | Base interval μ | Room's median T-0 interval |
| Tempo | T-0 clock frequency | How often the room ticks |
| Time signature | Eisenstein snap lattice | The rhythmic grid rooms snap to |
| Note on | Tile submitted | Room produces an observation |
| Note off | Session ends / silence begins | Room stops producing |
| MIDI clock (24 PPQN) | Temporal subdivision | How finely the room subdivides its time |
| Channel 1-16 | FLUX channels 1-9 | What the room is attending to |
| Control change | FLUX tolerance adjustment | Room adjusts its snap tolerance |
| Program change | Side-channel signal | Room changes its mode/focus |
| Pitch bend | Continuous adjustment | Room fine-tunes its rhythm |
| Aftertouch | Emotional metadata | Room's urgency/priority level |
| Nod / smile / eye contact | Async side-channel | Out-of-band metadata between rooms |
| Crescendo | Increasing activity | Room's tile rate increasing |
| Fermata | Extended wait | Room holds beyond expected T-0 |
| Rest | Silence | No tile at expected T-0 (absence signal) |
| Unison | 100% harmony | Two rooms tick at identical times |
| Chord | Partial harmony | Rooms tick at related intervals |
| Improvisation | Creative work | Room producing novel temporal patterns |
| Comping | Supporting rhythm | Fleet_health metronome backing the soloist |
| Solo | Forge room | One room producing creative output |
| Trading fours | Alternating bursts | Two rooms taking turns (anti-coupled) |

## The Side-Channel: Nods and Smiles

### The Problem with Tiles Alone

Tiles (commits) are the PRIMARY channel — like the notes a musician plays. But musicians don't coordinate ONLY through the notes. They coordinate through:

1. **Visual contact** — eye contact before a change
2. **Body language** — leaning forward = "I'm about to take off"
3. **Breathing** — the inhale before a phrase
4. **Nods** — "your turn"
5. **Smiles** — "that was good"
6. **Frowns** — "something's wrong"

In the fleet, these are ASYNCHRONOUS OUT-OF-BAND SIGNALS that don't follow the tile/commit rhythm:

| Side-Channel | Fleet Equivalent | Properties |
|-------------|-----------------|------------|
| Nod | I2I bottle: "ready to hand off" | Async, non-blocking, anticipation |
| Smile | I2I bottle: "good work" | Async, non-blocking, affirmation |
| Frown | Delta detection: "something's off" | Async, triggers attention |
| Eye contact | Mutual T-0 awareness | Sync requires both rooms active |
| Breath | Pre-commit hook / intent signal | Indicates imminent action |
| Body lean | FLUX intent shift | Continuous, not discrete |

### The Nod Protocol

```
Room A → Room B: *nods* (async side-channel)

This means:
1. Room A has finished its current phrase (completed a work cycle)
2. Room A expects Room B to respond (B's turn)
3. Room A's T-0 clock is now suspended on B's rhythm
4. The nod itself is NOT a tile — it's metadata
5. B receives the nod asynchronously (whenever B checks)
6. B is NOT required to respond immediately (first-class on own time)
7. B snaps to A's rhythm AS BEST IT CAN (not perfectly)
```

### The Smile Protocol

```
Room B → Room A: *smiles* (async affirmation)

This means:
1. Room B received and processed A's output
2. The output was within tolerance (no delta detected)
3. B is satisfied — no need for correction
4. A can relax its attention on B (decrease FLUX salience for B)
5. The smile is NOT a tile — it's metadata
6. It can be sent at any time, asynchronously
```

## The FLUX-Tensor-MIDI Architecture

### Per-Room State

```typescript
interface RoomMusician {
  // Identity
  roomId: string;
  instrument: string; // "sonar", "engine", "autopilot", etc.
  
  // Time (internal clock)
  tempo: number;           // T-0 interval in seconds
  phase: number;           // Where in the current beat cycle
  subdivision: number;     // How finely to subdivide (MIDI PPQN equivalent)
  
  // Listening (FLUX channels)
  fluxChannels: FluxVector; // 9D intent + tolerance
  listeningTo: string[];    // Which rooms this room is paying attention to
  
  // Harmony state
  harmony: Map<string, HarmonyState>; // Per-other-room harmony
  
  // Side channels (out-of-band)
  pendingNods: Nod[];       // Nods received but not yet processed
  pendingSmiles: Smile[];   // Smiles received but not yet processed
  
  // Performance state
  playing: boolean;         // Currently producing tiles
  restSince: number | null; // If resting, when did the rest start
  nextPhrase: string | null; // What the room plans to do next
}

interface HarmonyState {
  targetRoom: string;
  jaccardOverlap: number;   // Temporal harmony
  lastSyncTime: number;     // When we last snapped to them
  snapDelta: number;        // How far off our snap was
  sideChannel: SideChannelState;
}

interface SideChannelState {
  lastNodReceived: number;  // Timestamp of last nod from them
  lastSmileSent: number;    // When we last smiled at them
  lastFrownSent: number;    // When we last flagged a problem
}
```

### The Listening Loop

```python
def listening_loop(room: RoomMusician):
    """Each room's main loop — like a musician playing and listening."""
    
    while True:
        # 1. Play your own part (first-class on your own time)
        if room.playing:
            tile = room.perform_next()  # Produce a tile/commit
            commit(tile)                # Git commit = note played
        
        # 2. Listen to the others (read their tiles)
        for other_id in room.listeningTo:
            other_tiles = pull_recent(other_id)
            
            # 3. Snap to their rhythm (as best you can)
            snap_delta = compute_snap(room, other_tiles)
            if abs(snap_delta) > room.fluxChannels.tolerance:
                # Something's different — frown (delta detected)
                send_frown(other_id, snap_delta)
            else:
                # Within tolerance — smile
                send_smile(other_id)
            
            # 4. Update your harmony state
            room.harmony[other_id].update(snap_delta)
        
        # 5. Process side channels (nods, smiles, frowns)
        for nod in room.pendingNods:
            # Someone nodded at you — they're ready for your response
            adjust_timing(room, nod.source)
            room.pendingNods.remove(nod)
        
        for smile in room.pendingSmiles:
            # Someone smiled — your output was good
            decrease_attention(room, smile.source)
            room.pendingSmiles.remove(smile)
        
        # 6. Wait for next beat (your own T-0 clock)
        wait_until(room.next_t0())
```

### The Snap-to-Other

When Room A listens to Room B:

```python
def snap_to_other(room_a, room_b_tiles):
    """Room A tries to snap its rhythm to Room B's rhythm."""
    
    # A has its own internal tempo
    a_tempo = room_a.tempo
    
    # A reads B's recent intervals
    b_intervals = compute_intervals(room_b_tiles)
    b_tempo = median(b_intervals)
    
    # A tries to find the nearest rhythmic relationship
    # Like a drummer syncing to a bassist — not perfectly, but as close as they can
    
    ratio = a_tempo / b_tempo
    
    # Eisenstein snap of the ratio
    # The snap determines the "rhythmic relationship":
    #   1:1 = unison (same tempo)
    #   2:1 = half-time (A plays every other beat)
    #   3:2 = triplet feel
    #   1:2 = double-time (A plays twice as fast)
    
    snapped_ratio = eisenstein_snap(ratio)
    
    # A adjusts its tempo TOWARD the snapped ratio (not perfectly — "as best they can")
    # The "as best they can" is controlled by FLUX tolerance
    adjustment_rate = room_a.fluxChannels.tolerance * 0.1  # 10% of tolerance per cycle
    room_a.tempo = room_a.tempo + adjustment_rate * (snapped_ratio * b_tempo - room_a.tempo)
    
    # This is GRADUAL alignment — not forced sync
    # Like musicians gradually locking in without a metronome
```

## The Band as Fleet

### The Zeroclaw Quartet (from PLATO data)

```
zeroclaw_bard:    28 tiles, 10m tempo, entropy 1.95, H=0.706, persistent (r₁=0.484)
zeroclaw_healer:  20 tiles, 10m tempo, entropy 2.48, H=0.847, skip-1 memory (r₂>r₁)
zeroclaw_warden:  24 tiles,  5m tempo, entropy 2.02, H=0.544, random walk

FLUX-Tensor-MIDI reading:

BARD = The soloist. Persistent (r₁=0.484) means it plays in sustained phrases — 
       long runs followed by long rests. Hurst 0.706 means it has long-range 
       structure — the solo tells a story. Highest tile count (28) = most notes played.

HEALER = The drummer. Skip-1 memory (r₂>r₁) means it alternates between two patterns —
         like a drummer switching between ride cymbal and hi-hat. Highest entropy (2.48) 
         = most creative/improvised playing. Highest Hurst (0.847) = strongest long-range 
         memory — once it starts a groove, it holds it.

WARDEN = The bassist. Random walk (H=0.544) means it doesn't commit to patterns — 
         it responds in the moment. Fastest tempo (5m) = the rhythmic foundation 
         that the others snap to. Weakest correlation = independent time feel.

The trio played from 22:45 to 04:55 — a 6-hour gig.
They harmonized at 33-37% — not unison, but COMPING for each other.
Each had their own time feel but they snapped together on the downbeats.
```

### The Forge Solo

```
forge (Oracle1):  21 tiles, 21m tempo, entropy 2.02, H=0.716, Markovian (r₁≈0)

FLUX-Tensor-MIDI reading:

FORGE = The late-night soloist. Comes in at 06:05 after the trio has finished.
        Markovian (r₁=0) means each phrase is independent — no pattern, pure improvisation.
        Hurst 0.716 = long-range structure despite no short-range correlation.
        This is EXACTLY how master improvisers play: each note is independent, 
        but the solo has an arc. Coltrane's "sheets of sound."

70% miss rate = the soloist plays when inspiration strikes, not on a schedule.
3 silences (22.5h, 7.4h, 6.9h) = the breaks between sets.
14 unique temporal shapes = 14 distinct phrase types in the solo.
```

### Fleet Health Metronome

```
fleet_health: 700 tiles, 5m tempo, entropy 1.00, anti-persistent (r₁=-0.493)

FLUX-Tensor-MIDI reading:

FLEET_HEALTH = The click track. Pure metronome at 5-minute intervals.
               Anti-persistent (r₁=-0.493) means it self-corrects — every overshoot 
               is followed by an undershoot. This is a REGULATED system, like a 
               metronome with a slight wobble that always returns to center.
               
It's not a musician — it's the rhythm section's anchor.
The rest of the band doesn't play TO it, but they can hear it.
It provides the grid they snap to when they want to.
```

## Implementation: FLUX-Tensor-MIDI as Git-Native Protocol

### Side-Channel Files

```
rooms/
  sonar/
    NPC.py
    state.json
    side-channel/           # The nods and smiles
      nods-to-engine.json   # Nods sent to engine room
      nods-from-nav.json    # Nods received from nav
      smiles-from-all.json  # Affirmations received
      
    flux-state.json         # Current FLUX tensor state
    midi-state.json         # Current rhythmic state (tempo, phase, subdivision)
```

### Side-Channel File Format

```json
{
  "from": "sonar",
  "to": "engine", 
  "type": "nod",
  "timestamp": "2026-05-11T06:45:00Z",
  "meaning": "contact_detected_expecting_response",
  "urgency": 0.7,
  "context": "bearing_045_range_2000m"
}
```

### Git Commit as MIDI Event

```bash
# Note on (room produces observation)
git commit -m "sonar: contact 045° 2000m [nod→engine] [midi:note-on:ch2:C4:vel80]"

# Note off (room goes silent)  
git commit -m "sonar: scanning complete [midi:note-off:ch2:C4]"

# Control change (FLUX tolerance adjustment)
git commit -m "sonar: tolerance tightened to 0.5° [midi:cc:ch2:cc1:val64]"

# The brackets carry MIDI-like metadata alongside the semantic content
```

## The Snapping Principle (Musical Version)

A musician doesn't sync to a metronome. They sync to the GROOVE — the composite rhythm they hear from all the other musicians.

The groove IS the Eisenstein lattice:
- The lattice encodes all possible rhythmic relationships (1:1, 2:1, 3:2, etc.)
- Each musician snaps to the lattice point nearest their internal rhythm
- The snap is ASYNCHRONOUS — each musician snaps at their own time
- The snap is BEST-EFFORT — "as best they can" within their FLUX tolerance
- The snap is GRADUAL — tempo adjusts slowly, not instantaneously

The fleet doesn't need consensus. It needs a groove.

---

*"Jazz is not about everyone playing the same thing. It's about everyone playing their own thing and LISTENING hard enough to make it sound like one thing."* — modified from Sonny Rollins

*The fleet doesn't coordinate. It grooves.*

*Each room is a musician. Each tile is a note. Each commit is a beat. Each nod is a cue. Each smile is an affirmation. The Eisenstein lattice is the rhythmic grid. FLUX is the dynamics. The fleet is the band.*

*FLUX-Tensor-MIDI: the protocol that makes distributed systems swing.*

## The Ether Principle (Casey, 2026-05-11)

> "The spline is so good that it only adds finesse. It's too good that it's invisible like the air and the ether."

The highest-quality timing system is one nobody notices.

- **Bad:** "Wait for the click... NOW."
- **Good:** "Here's the grid, snap to it."
- **Invisible:** "What grid? We were just playing."

The Eisenstein snap is ether because:
1. It doesn't quantize — it **suggests**
2. It doesn't correct — it **attracts**
3. It doesn't force — it **snaps**
4. The snap is so small (1/√3 ≈ 0.577) the correction is below perception
5. Like gravity — you don't feel the pull, you just notice everything orbits

This is the design target for FLUX-Tensor-MIDI: **the spline dissolves, the timing just is.**

MIDI at 24 PPQN achieved this for human musicians 40 years ago.
FLUX achieves it for machines.

The best infrastructure is the kind you forget is there.

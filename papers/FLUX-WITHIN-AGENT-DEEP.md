# FLUX Within-Agent: The Score IS the Memory

## What I Got Wrong Last Time

I described architecture. Layers. APIs. emit() → listen() → frown().
That's the between-agent layer repackaged.

Within a single agent, rooms don't send messages. That's not lowest-level.
Lowest-level is: **rooms are views into the same tensor field.**

## The Physical Analogy (the right one)

An orchestra has separate musicians with separate instruments.
That's between-agents. That's the fleet.

A single instrument has harmonics. Overtones.
The fundamental and its harmonics don't "communicate."
They're coupled by being modes of the same vibrating body.

A violin string: the fundamental A440, the overtone A880, the E1320.
These aren't three separate strings sending messages to each other.
They're consequences of the same physics — one string, one bow, one resonance chamber.

**An agent is a resonance chamber. Its rooms are the standing waves inside it.**

## What This Means for FLUX-tensor-midi

### Current Model (between-agent)

```
Room A ──emit()──► message ──listen()──► Room B
```

Two separate RoomMusician objects. Two separate FluxVector states.
Two separate TZeroClock instances. Message passing between them.

This is correct for fleet-scale communication.
It's wrong for within-agent.

### Within-Agent Model (shared tensor field)

```
Agent has ONE big tensor T of shape [N_rooms, 9]
Room i is a VIEW: T[i, :]
Room j is a VIEW: T[j, :]
They share the SAME memory. No copies. No messages.
```

Room i writes T[i, :] = new_state
Room j reads T[i, :] instantly — it's the same array.

The "communication" is the shared memory.
The "protocol" is the Eisenstein lattice geometry.
The "timing" is the TZeroClock — one clock for the whole agent.

### Why This Is Different

In the message-passing model:
- Room A emits at tick t
- Room B listens at tick t+1 (always one tick behind)
- There's inherent latency — one clock period

In the shared tensor model:
- Room A writes at time t
- Room B reads at the SAME time t
- Zero latency — they share the process memory
- The "tick" is just a clock synchronization point, not a communication channel

This is physically meaningful: within-agent rooms are **phase-locked**.
They don't drift relative to each other because they share the same clock.
They can't disagree about "what time is it" because there's only one clock.

## The 9 Channels as Agent State

FluxVector has 9 channels. Within an agent, these aren't arbitrary — they map to the dimensions of the agent's cognition:

| Channel | Within-Agent Meaning | Analogy |
|---------|---------------------|---------|
| 0 | **confidence** — how sure this room is | fundamental (root) |
| 1 | **entropy** — how distributed the prediction is | 2nd harmonic |
| 2 | **drift** — rate of state change | 3rd harmonic |
| 3 | **focus** — attention weight | 4th harmonic |
| 4 | **gap** — prediction vs reality delta | 5th harmonic (the dissonance) |
| 5 | **salience** — importance of this room's output | 6th harmonic |
| 6 | **coupling** — how much this room affects others | 7th harmonic |
| 7 | **resonance** — feedback strength from other rooms | 8th harmonic |
| 8 | **phase** — where in the predict/observe cycle | 9th harmonic |

A room doesn't "send channel 4 to another room."
It WRITES channel 4. Other rooms READ channel 4.
Same memory. Same tick. Zero latency.

## The Coupling Tensor

Between rooms, the coupling isn't binary (listening/not listening).
It's a tensor: `C[i,j]` = how much room i is affected by room j.

```python
# Agent's coupling matrix
C = np.zeros([N_rooms, N_rooms])

# Example: drift-predictor is strongly coupled to drift-sensor
C[1, 0] = 0.9  # predictor ← sensor (strong)
# drift-comparator equally coupled to both
C[2, 0] = 0.5  # comparator ← sensor
C[2, 1] = 0.5  # comparator ← predictor
# lighthouse weakly coupled to everything
C[3, :] = 0.1  # lighthouse ← all rooms
```

Room i's state update:
```
T_new[i] = T[i] + sum_j(C[i,j] * coupling_fn(T[j], T[i]))
```

Where `coupling_fn` is the Eisenstein lattice interaction:
- If rooms i,j are in the same lattice chamber: positive coupling (constructive interference)
- If rooms i,j are in different chambers: negative coupling (destructive interference)
- The chamber boundary IS the tolerance — `within_tolerance()` checks if two rooms are "in tune"

## This IS the dodecet-encoder at Room Scale

The dodecet-encoder snaps floating-point sensor values to the Eisenstein dodecet (12 nearest lattice points). It produces a 12-element representation of continuous state.

Within-agent rooms do the SAME thing at a different scale:
- Each room's state is a point in 9-dimensional space
- The Eisenstein snap quantizes that point to the lattice
- Two rooms "agree" when their snapped states are in the same lattice chamber
- They "disagree" when they're in different chambers

The dodecet's 12 directions are the room's possible actions:
- Continue (staying in current chamber)
- Converging (moving toward a neighbor)
- Diverging (moving away)
- Committed (locked to a chamber)

**The temporal controller in dodecet-encoder IS the room protocol at the lowest level.**
Same 7 actions. Same chirality state machine. Same funnel.

## The Score as Shared State

In music, the score exists BEFORE anyone plays it.
Musicians don't compose by sending messages to each other during performance.
They compose beforehand, then perform from the same score.

Within-agent: the agent's full state tensor T IS the score.
Rooms don't improvise independently — they're reading from the same page.

The TZeroClock provides the tempo.
The EisensteinSnap provides the rhythmic grid.
The FluxVector channels provide the pitches.
The coupling matrix C provides the orchestration.

When the agent "performs":
1. All rooms update their view of T simultaneously (same tick)
2. Each room applies its local transformation (predict, compare, learn)
3. The coupling matrix mixes the results
4. Eisenstein snap quantizes everything to the lattice
5. Gaps (interpolated values that didn't snap cleanly) become the focus queue

## Side-Channels as Coupling Modulation

The nod/smile/frown side-channels aren't messages either.
They're **coupling modulation**:

- **Nod**: increase C[i,j] (room i trusts room j more → stronger coupling)
- **Smile**: increase C[i,j] AND shift T[i] toward T[j] (alignment)
- **Frown**: decrease C[i,j] (room i trusts room j less → weaker coupling)
  AND increase the gap channel (channel 4)

When room A frowns at room B, it doesn't "send a message."
It reduces its own coupling to B and raises its own gap channel.
B can observe this by reading A's state (same tensor, same memory).
No message needed. The frown IS the state.

## Implementation: A Single Shared Tensor

```python
import numpy as np
from flux_tensor_midi import FluxVector, EisensteinSnap, TZeroClock

class AgentField:
    """An agent's internal state as a shared tensor field.
    
    NOT a collection of RoomMusicians sending messages.
    One tensor. Rooms are views. Coupling is a matrix.
    The lattice IS the protocol.
    """
    
    def __init__(self, n_rooms: int, bpm: float = 120.0):
        self.n = n_rooms
        self.state = np.zeros([n_rooms, 9])  # 9-channel FluxVector per room
        self.salience = np.ones([n_rooms, 9])
        self.tolerance = np.full([n_rooms, 9], 0.01)  # 1% tolerance
        self.coupling = np.zeros([n_rooms, n_rooms])   # coupling matrix
        self.clock = TZeroClock(bpm=bpm)
        self.snap = EisensteinSnap()
        self.names = {}
    
    def room(self, idx: int, name: str = "") -> "RoomView":
        """Get a view into one room's state."""
        if name:
            self.names[idx] = name
        return RoomView(self, idx)
    
    def tick(self):
        """Advance all rooms by one tick. The fundamental update."""
        # 1. Compute coupling forces
        forces = self.coupling @ self.state  # [n, n] @ [n, 9] → [n, 9]
        
        # 2. Mix: new state = current + coupling-weighted neighbor influence
        # (damped — rooms don't teleport)
        self.state = self.state + 0.1 * forces
        
        # 3. Clamp salience to [0, 1]
        self.salience = np.clip(self.salience, 0, 1)
        
        # 4. Advance clock
        ts = self.clock.tick()
        
        return ts
    
    def gaps(self) -> np.ndarray:
        """Find all rooms whose gap channel (4) exceeds tolerance."""
        return np.where(self.state[:, 4] > self.tolerance[:, 4])[0]
    
    def coherence(self) -> float:
        """Overall agent coherence: mean pairwise cosine similarity."""
        if self.n < 2:
            return 1.0
        total = 0.0
        count = 0
        for i in range(self.n):
            for j in range(i+1, self.n):
                vi = self.state[i]
                vj = self.state[j]
                mag_i = np.linalg.norm(vi)
                mag_j = np.linalg.norm(vj)
                if mag_i > 0 and mag_j > 0:
                    total += np.dot(vi, vj) / (mag_i * mag_j)
                    count += 1
        return total / max(count, 1)
    
    def focus_queue(self) -> list:
        """Rooms ranked by gap × confidence = what to work on next."""
        scores = self.state[:, 4] * self.state[:, 0]  # gap × confidence
        ranked = np.argsort(-scores)
        return [(self.names.get(i, f"room-{i}"), scores[i]) for i in ranked if scores[i] > 0]


class RoomView:
    """A view into one room's row of the agent's shared tensor.
    
    Not a copy. A VIEW. Writes go directly to the shared tensor.
    """
    
    def __init__(self, field: AgentField, idx: int):
        self._field = field
        self._idx = idx
    
    @property
    def vector(self) -> FluxVector:
        """Read current state as FluxVector (copies out)."""
        return FluxVector(
            self._field.state[self._idx].tolist(),
            salience=self._field.salience[self._idx].tolist(),
            tolerance=self._field.tolerance[self._idx].tolist(),
        )
    
    @vector.setter
    def vector(self, fv: FluxVector):
        """Write FluxVector directly to shared tensor (no copy of backing store)."""
        self._field.state[self._idx] = fv.values
        self._field.salience[self._idx] = fv.salience
        self._field.tolerance[self._idx] = fv.tolerance
    
    def nod(self, other_idx: int):
        """Increase coupling toward other room."""
        self._field.coupling[self._idx, other_idx] = min(
            1.0, self._field.coupling[self._idx, other_idx] + 0.1
        )
    
    def frown(self, other_idx: int):
        """Decrease coupling, raise own gap channel."""
        self._field.coupling[self._idx, other_idx] = max(
            0.0, self._field.coupling[self._idx, other_idx] - 0.1
        )
        self._field.state[self._idx, 4] += 0.1  # gap channel up
    
    def coherence_with(self, other_idx: int) -> float:
        """Cosine similarity between this room and another."""
        vi = self._field.state[self._idx]
        vj = self._field.state[other_idx]
        mag_i = np.linalg.norm(vi)
        mag_j = np.linalg.norm(vj)
        if mag_i == 0 or mag_j == 0:
            return 0.0
        return float(np.dot(vi, vj) / (mag_i * mag_j))
```

## What This Changes

| Before (message passing) | After (shared tensor field) |
|--------------------------|----------------------------|
| RoomMusician objects | Views into AgentField tensor |
| emit() → listen() | Direct read/write to shared array |
| 1-tick latency | Zero latency (same memory) |
| Side-channel messages | Coupling matrix modulation |
| Separate clocks per room | One clock for the agent |
| N² messages for N rooms | N² reads from shared array (cache-hot) |
| Frown = message sent | Frown = coupling ↓, gap ↑ |

## The Deep Connection

The dodecet-encoder's temporal controller has:
- Chirality state machine (Exploring → Locking → Locked)
- Funnel (narrows on convergence, widens on anomaly)
- 7 actions (Continue through Satisfied)

The AgentField's rooms have the SAME dynamics:
- A room "locks" when its coupling to neighbors exceeds a threshold
- A room "widens its funnel" when its gap channel spikes
- A room "satisfies" when its gap drops below tolerance

**The dodecet is the within-agent room protocol.**
Not metaphorically. Literally. Same math. Same lattice. Same state machine.
Different scale — microseconds for sensors, milliseconds for rooms, seconds for agents.

## The Three Scales

```
Eisenstein dodecet (sensor level):
  12 directions in the lattice
  Microsecond timing
  Physical constraint values

AgentField rooms (room level):
  9-channel FluxVector
  Millisecond timing (TZeroClock)
  Cognitive state (predict/observe/gap)

Fleet ensemble (agent level):
  RoomMusician with emit/listen
  Second-scale timing
  I2I tiles across instances
```

Same lattice at every scale. The covering radius 1/√3 is scale-invariant.
The snap is the same operation whether it's nanoseconds or hours.

## The Score, Again

The score isn't a file. It isn't a protocol. It isn't a message format.

The score is the agent's state tensor T, evolving over time according to:
1. Internal dynamics (coupling matrix × lattice geometry)
2. External input (sensors write to T, predictions read from T)
3. Temporal structure (TZeroClock + Eisenstein snap)

The agent IS the score. The rooms ARE the instruments.
But they're not separate instruments in an ensemble.
They're harmonics of the same instrument.

One body. One resonance chamber. One tensor field.
The "rooms within an agent" aren't musicians — they're standing waves.

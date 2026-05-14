# Chapter 5: Within-Agent Coordination — AgentField

## 5.1 Introduction

The preceding chapters established the PLATO room abstraction—a model of intelligent agents as collections of semi-autonomous processing units (rooms) that coordinate through structured tile exchange. We now confront a subtler architectural question: how do the rooms *within a single agent* coordinate their internal states without incurring the overhead of message-passing infrastructure?

This chapter introduces the **AgentField**, a shared tensor field model that replaces message passing with matrix operations. Rather than treating rooms as independent actors communicating through channels, AgentField treats the agent itself as a continuous medium—a resonance chamber—within which rooms exist as standing wave patterns. Coordination is not achieved by sending messages but by modulating the coupling between regions of a shared state tensor.

The design draws on three observations. First, the cost of message passing scales quadratically with the number of rooms: for $N$ rooms, maintaining pairwise communication channels requires $O(N^2)$ message handlers and a corresponding routing infrastructure. Second, even optimized message queues impose a minimum one-tick latency—a room cannot act on information until the next scheduling cycle, creating artificial temporal gaps in what should be a continuous process. Third, and most fundamentally, rooms within a single agent share a common operational context: they operate on overlapping aspects of the same reality. The information they exchange is not arbitrary but structurally constrained—a sensor's confidence in its reading, a predictor's uncertainty about an outcome, a comparator's assessment of the gap between expectation and observation.

These observations motivate a radical simplification: if rooms share context and their information exchange is structurally constrained, we can represent the entire agent's internal state as a single two-dimensional array and let rooms operate as views (slices) into this array rather than as independent entities with their own state.

## 5.2 The Shared Tensor Field Model

The AgentField maintains a single state array of shape $[N, 9]$, where $N$ is the number of rooms and 9 is the number of semantic channels. Each room is an index into this array. Reading a room's state is a zero-copy slice operation. Writing to a room modifies the shared array directly. There is no message queue, no routing table, and no serialization overhead.

```python
class AgentField:
    def __init__(self, bpm=120.0, damping=0.1):
        self._n = 0
        self._state: List[List[float]] = []      # [room][channel]
        self._coupling: List[List[float]] = []    # [room_from][room_to]
```

The crucial design decision is that rooms are *views, not copies*. When a sensor room writes new observations, the predictor room that is coupled to it sees the update on the very next tick—not after a message has been composed, serialized, placed in a queue, and dequeued. The coupling matrix $C[i,j]$ determines how strongly room $i$ is influenced by room $j$, and the update rule is a single matrix operation:

$$s_i^{(t+1)}[ch] = s_i^{(t)}[ch] + \sum_{j \neq i} C[i,j] \cdot (s_j^{(t)}[ch] - s_i^{(t)}[ch]) \cdot \alpha$$

where $\alpha$ is a damping coefficient that prevents runaway feedback. This is not message passing reformulated—it is diffusion. Information flows through the field like heat through a conductor, modulated by the coupling strengths that define the agent's internal topology.

The coupling matrix itself is sparse and directed. $C[i,j] \neq C[j,i]$ in general: a predictor room may be strongly influenced by a sensor room ($C[\text{pred}, \text{sensor}] = 0.9$) while the sensor is entirely unaffected by the predictor ($C[\text{sensor}, \text{pred}] = 0.0$). This asymmetry is essential—it allows the field to implement directed information flow without any explicit routing logic.

## 5.3 The Nine Channels

The choice of nine channels is not arbitrary. Each channel captures a distinct dimension of a room's operational state, and together they provide a complete description of the room's relationship to the agent's overall cognitive process.

**Channel 0: Confidence.** How certain is this room about its current output? A sensor reports confidence based on signal quality; a predictor reports confidence based on historical accuracy; a comparator reports confidence based on the clarity of its comparison. This channel drives the focus computation: a room that is highly confident but wrong is more interesting than one that is uncertain and wrong.

**Channel 1: Entropy.** How distributed is the room's prediction? A room that predicts a single outcome with certainty has low entropy; one that assigns equal probability to many outcomes has high entropy. Entropy serves as a proxy for model complexity and uncertainty—when entropy spikes, the room is operating in a regime its model doesn't cover well.

**Channel 2: Drift.** What is the rate of change in this room's state? Drift captures temporal dynamics—a room whose output is changing rapidly is in a different operational mode than one that is stable. High drift in a sensor indicates a changing environment; high drift in a predictor indicates a shifting model.

**Channel 3: Focus.** The attention weight assigned to this room by the agent's global attention mechanism. Focus is not set by the room itself but emerges from the interplay of gap signals, coupling, and the agent's current task. A room with high focus is one the agent is actively relying on.

**Channel 4: Gap.** The difference between prediction and reality. This is the channel that connects within-agent coordination to the collective inference framework described in Chapter 8. A non-zero gap value indicates that the room's model is incomplete—that there is something in the environment the room did not predict. The gap channel is, in a sense, the most important channel: it is the negative space, the shape of what the agent doesn't know.

**Channel 5: Salience.** How important is this room's output relative to the agent's current goals? Salience gates the coupling: a room with low salience can be coupled to many others without causing interference, because its contributions are downweighted. Salience is per-channel, allowing fine-grained control over which aspects of a room's state propagate through the field.

**Channel 6: Coupling.** The room's self-assessed coupling strength—a measure of how much it believes it should be influenced by other rooms. This is distinct from the coupling matrix $C[i,j]$ (which is set by the agent's wiring) and represents the room's dynamic willingness to be influenced. A room that has detected an anomaly may raise its coupling to listen more carefully to its neighbors.

**Channel 7: Resonance.** The feedback strength the room receives from other rooms. Resonance is the inbound complement of coupling—if room $i$ has high resonance, it means other rooms are paying attention to it. High resonance indicates a room that is central to the agent's current operation.

**Channel 8: Phase.** Where in the predict-observe cycle is this room? Phase is a cyclic value in $[0, 1)$ representing the four stages of the simulation-first loop: perceiving (0.0), predicted (0.25), comparing (0.5), and learning (0.75). Phase ensures that coupled rooms synchronize their operational cycles—a predictor should not be reading from a sensor that is mid-comparison.

The number nine emerged from iterative refinement. Earlier designs used seven channels (omitting resonance and phase) and suffered from synchronization failures between coupled rooms. Adding phase solved the synchronization problem, and adding resonance provided the necessary feedback signal for the coupling dynamics to stabilize. The result is a minimal but complete description of room state.

## 5.4 The Coupling Matrix and the Elimination of Message Passing

The coupling matrix $C$ is the central data structure of the AgentField. It is an $N \times N$ matrix where entry $C[i,j]$ represents the strength with which room $i$ is influenced by room $j$. The matrix is sparse (most rooms are only coupled to a few others), directed ($C[i,j] \neq C[j,i]$ in general), and dynamically modifiable (coupling strengths change as the agent operates).

The `tick()` method implements the fundamental update:

```python
def tick(self) -> float:
    new_state = [list(row) for row in self._state]
    for i in range(self._n):
        for j in range(self._n):
            if i == j or self._coupling[i][j] == 0:
                continue
            c = self._coupling[i][j]
            for ch in range(9):
                diff = self._state[j][ch] - self._state[i][ch]
                new_state[i][ch] += c * diff * self._damping
    for i in range(self._n):
        for ch in range(9):
            s = self._salience[i][ch]
            self._state[i][ch] = new_state[i][ch] * s
```

This is a single-pass diffusion update. Compare this with the equivalent message-passing implementation:

1. Each room composes a message containing its state.
2. Each room checks its inbox for messages from coupled rooms.
3. Each room parses incoming messages, weights them by coupling strength, and updates its state.
4. A scheduler ensures all rooms have completed step 3 before any room begins step 1 of the next tick.

Steps 1–4 require serialization, deserialization, queue management, and synchronization primitives. The diffusion update requires a nested loop over the coupling matrix. For an agent with $N$ rooms and $k$ non-zero coupling entries, the diffusion update is $O(k \cdot 9)$; the message-passing approach is $O(k)$ messages plus $O(k)$ deserializations plus $O(N)$ synchronization barriers. The constant factors favor diffusion overwhelmingly.

Moreover, the diffusion update has a natural physical interpretation. The coupling matrix defines a weighted directed graph over the rooms. Each tick propagates information along the edges of this graph, with the damping coefficient controlling the speed of propagation. This is precisely the dynamics of heat diffusion on a graph, and the same mathematical tools—spectral analysis, convergence guarantees, steady-state computation—apply directly.

## 5.5 Side-Channels as Coupling Modulation

In message-passing architectures, "side-channels" are auxiliary communication paths that carry metadata: acknowledgments, priority flags, emotional valence. The PLATO fleet uses three such channels: **nod** (acknowledgment), **smile** (approval), and **frown** (disapproval).

In the AgentField, side-channels are not messages. They are *coupling modulations*—operations that modify the coupling matrix rather than sending data through it.

```python
def nod(self, from_room, to_room, intensity=0.1):
    """Increase coupling (trust more)."""
    i, j = self.idx(from_room), self.idx(to_room)
    self._coupling[i][j] = min(1.0, self._coupling[i][j] + intensity)

def smile(self, from_room, to_room, intensity=0.1):
    """Increase coupling AND shift toward other room's state."""
    i, j = self.idx(from_room), self.idx(to_room)
    self._coupling[i][j] = min(1.0, self._coupling[i][j] + intensity)
    for ch in range(9):
        diff = self._state[j][ch] - self._state[i][ch]
        self._state[i][ch] += diff * intensity * 0.5

def frown(self, from_room, to_room, intensity=0.1):
    """Decrease coupling AND raise gap channel."""
    i, j = self.idx(from_room), self.idx(to_room)
    self._coupling[i][j] = max(0.0, self._coupling[i][j] - intensity)
    self._state[i][4] += intensity
```

A **nod** from room $i$ to room $j$ increases $C[i,j]$—room $i$ will be more influenced by room $j$ in future ticks. This is trust: "I believe your output is relevant to my operation."

A **smile** does everything a nod does, plus it immediately shifts room $i$'s state toward room $j$'s state. This is alignment: "Not only do I trust you, but I'm going to start matching you right now."

A **frown** decreases coupling and raises the gap channel. This is distrust: "I no longer believe your output is relevant, and I'm flagging a gap in my understanding that your output should have filled."

The side-channel abstraction demonstrates a key advantage of the field model: operations that would require separate message types, handlers, and routing logic in a message-passing system reduce to simple matrix operations. The semantics are preserved (nod still means acknowledgment, smile still means approval, frown still means disapproval), but the implementation is unified.

## 5.6 Chirality: The Phase State Machine

Rooms in the AgentField exhibit a three-state chirality cycle derived from the dodecet-encoder's temporal controller:

$$\text{exploring} \xrightarrow{\text{gap} < \text{tol},\ 3+\text{ticks}} \text{locking} \xrightarrow{\text{gap} < \text{tol},\ 10+\text{ticks}} \text{locked} \xrightarrow{\text{gap} > \text{tol}} \text{exploring}$$

An **exploring** room is searching for stable behavior. Its gap channel is above tolerance, indicating that its predictions don't match observations. The room's coupling is typically low—it's not yet sure which other rooms to trust.

A **locking** room has found approximately correct behavior (gap below tolerance for at least 3 ticks) but hasn't confirmed it. Its coupling is increasing as it begins to trust the rooms whose outputs align with its own.

A **locked** room has stable behavior (gap below tolerance for at least 10 ticks). Its coupling is at its strongest, and it contributes reliably to the field's overall state. Locked rooms form the backbone of the agent's cognitive process.

The critical transition is **locked → exploring**, triggered when gap exceeds tolerance. This is anomaly detection: a room that was behaving correctly suddenly isn't. The transition resets the room's coupling (it can no longer trust its previous neighbors) and flags the gap for attention. In the focus queue, this room will receive high priority—its confidence (built up over 10+ ticks of stable operation) multiplied by its suddenly large gap produces a focus score that demands investigation.

The chirality state machine provides a natural mechanism for graceful degradation. An agent with many locked rooms and a few exploring ones is operating normally—the exploring rooms are handling edge cases or novel situations. An agent with many exploring rooms and few locked ones is in trouble—something fundamental has changed in the environment that has disrupted most of its models.

## 5.7 The Physical Analogy: Standing Waves in a Resonance Chamber

The AgentField's design is informed by a physical analogy that distinguishes it from conventional agent architectures. In a traditional multi-agent system, each agent (or room) is like a musician in an ensemble: it has its own instrument (state), reads from a score (input), produces sound (output), and listens to other musicians (communication). Coordination is achieved through a conductor (scheduler) who ensures everyone plays at the right time.

The AgentField rejects this metaphor. Instead, it models the agent as a **resonance chamber** and rooms as **standing wave patterns** within that chamber. A standing wave is not an independent entity—it is a pattern that emerges from the interaction of the chamber's geometry (coupling topology), the excitation frequency (tick rate), and the medium's properties (damping, salience). No two standing waves are independent: they all exist within the same medium, and perturbing one affects all others through the shared medium.

This analogy has several consequences:

1. **No conductor needed.** Standing waves synchronize naturally through the medium. There is no central scheduler deciding which room updates when—the tick advances all rooms simultaneously through the diffusion update.

2. **Harmonics are meaningful.** The four-phase cycle (perceiving, predicted, comparing, learning) corresponds to the fundamental harmonic of the field. Rooms at different phases are like overtones—they contribute different frequency components to the agent's overall state. Phase alignment (locking and locked rooms sharing the same phase) is analogous to resonance.

3. **Damping is essential.** Without damping, any perturbation would propagate indefinitely, making the field unstable. The damping coefficient $\alpha$ plays the same role as the Q-factor in a physical resonator: it determines how quickly the field settles after a perturbation.

4. **Coupling is the geometry.** The coupling matrix defines the shape of the resonance chamber. Rooms with strong mutual coupling are like the ends of a vibrating string—what happens at one end directly affects the other. Rooms with weak coupling are like distant points on a membrane—their interaction is attenuated.

The resonance chamber analogy is not merely poetic. It provides a rigorous mathematical framework: the eigenvalues of the coupling matrix determine the field's resonant frequencies, the damping coefficient determines its stability, and the convergence properties of the diffusion update are guaranteed by the same theorems that guarantee convergence of heat diffusion.

## 5.8 Comparison with Existing Architectures

### Actor Model (Hewitt, 1973)

The actor model treats each computational entity as an independent actor that communicates through asynchronous message passing. Each actor has its own state, processes messages one at a time, and can create new actors. The AgentField shares the actor model's emphasis on encapsulation (a room's internal state is accessed through the field's API) but differs fundamentally in its communication model: actors send messages; rooms share a medium. The actor model's strength is distributed systems where entities are physically separated; the AgentField's strength is within-agent coordination where entities share memory.

### Communicating Sequential Processes (Hoare, 1978)

CSP models concurrent computation as sequential processes that communicate through synchronous channels. Each process runs independently until it reaches a communication point, at which it blocks until its counterpart is ready. CSP's channels are point-to-point and unbuffered; the AgentField's coupling is broadcast (all coupled rooms see updates simultaneously) and continuous (there is no blocking). CSP is better suited for pipeline architectures where data flows through well-defined stages; the AgentField is better suited for feedback-rich architectures where rooms influence each other bidirectionally.

### Blackboard Systems (Engelmore & Morgan, 1988)

Blackboard systems are the closest architectural relative of the AgentField. A blackboard is a shared data structure that multiple knowledge sources (analogous to rooms) read from and write to. A control mechanism determines which knowledge source acts next based on the current state of the blackboard. The key difference is that blackboard systems still use a scheduler: the control mechanism decides who acts. The AgentField has no scheduler—*all* rooms update simultaneously through the diffusion rule. The blackboard is passive (it stores data but doesn't process it); the AgentField is active (the diffusion update is itself a computation).

The following table summarizes the comparison:

| Property | Actor Model | CSP | Blackboard | AgentField |
|---|---|---|---|---|
| Communication | Messages | Channels | Shared data | Shared tensor |
| Scheduling | Per-actor | Per-process | Central control | Simultaneous |
| Latency | ≥ 1 tick | ≥ 1 tick | Variable | 0 (same tick) |
| Complexity (N rooms) | O(N²) messages | O(N) channels | O(N) reads | O(k) diffusion |
| Feedback | Explicit | Explicit | Explicit | Implicit (coupling) |

## 5.9 The Gap Channel and Negative Space

Channel 4 (gap) deserves special attention because it connects the within-agent coordination model to the broader theme of constraint theory and negative space that runs through this dissertation.

In constraint theory, a constraint is defined not by what it permits but by what it excludes—the negative space around the feasible region. Similarly, the gap channel captures not what the room knows but what it *doesn't* know: the difference between its prediction and reality. A room with zero gap is a room whose model perfectly explains its observations; a room with non-zero gap is a room whose model has a hole.

The focus queue operationalizes this insight. It ranks rooms by $focus\_score = gap \times confidence$—the product of how wrong the room is and how sure it was. This formula encodes a specific epistemic principle: the most valuable signal is not the unexpected observation from an uncertain room, but the *confidently wrong* prediction from a previously reliable room. The confident failure is the "missing word" in the room's model—the place where the model's assumptions break down.

This connects directly to the negative space theory of Chapter 3. There, constraints were understood as boundaries of the feasible region. Here, gaps are understood as boundaries of the room's knowledge. The parallel is exact: just as a constraint is the shape of what's not possible, a gap is the shape of what's not understood. The AgentField's focus queue is a constraint-satisfaction mechanism that directs the agent's attention to the largest unexplored regions of its knowledge space.

## 5.10 Implementation and Testing

The AgentField is implemented in approximately 280 lines of pure Python (no NumPy dependency) in the `agent_field.py` module of the plato-training package. The implementation uses nested lists for the state array and coupling matrix, with explicit indexing operations rather than array slicing. This is a deliberate design choice: the module is intended to be deployable on any Python runtime, including the constrained environments (microcontrollers, embedded systems) targeted by the PLATO micro-model pipeline.

The test suite comprises 35 tests organized into seven categories:

1. **Room lifecycle** (5 tests): adding rooms, resolving indices, duplicate handling.
2. **State access** (5 tests): reading and writing channels, FluxVector compatibility.
3. **Coupling dynamics** (6 tests): directed coupling, symmetric coupling, decoupling.
4. **Side-channel operations** (5 tests): nod/smile/frown semantics and coupling modulation.
5. **Tick and diffusion** (5 tests): single-tick updates, multi-tick convergence, damping effects.
6. **Coherence and gap analysis** (5 tests): pairwise coherence, gap detection, focus queue ordering.
7. **Chirality state machine** (4 tests): exploring→locking→locked transitions, anomaly-triggered reset.

All 35 tests pass. The test suite validates not only functional correctness but also the emergent properties of the field: that coupled rooms converge to similar states over multiple ticks, that the focus queue correctly prioritizes confident failures, and that the chirality state machine transitions correctly under both normal and anomalous conditions.

Integration with the collective inference framework (Chapter 8) is achieved through the gap channel and focus queue. When a SimulationRoom detects a gap between prediction and observation, it writes the gap to the AgentField's gap channel. The field's focus queue then determines which gaps receive attention, and the coupling dynamics ensure that rooms related to the gapped room are influenced to help resolve it. This creates a feedback loop: gap detection → focus → attention → coupling modulation → updated predictions → reduced gap.

## 5.11 Limitations and Future Work

The current AgentField implementation has several limitations that suggest directions for future work.

**Linear coupling.** The diffusion update is linear in the state differences. This limits the field's ability to model nonlinear interactions between rooms. A natural extension is to replace the linear coupling with a learned coupling function $f(s_i, s_j)$ parameterized by a small neural network. This would allow the field to capture interactions that the current linear model cannot.

**Static topology.** The coupling matrix is modified only through explicit side-channel operations (nod/smile/frown). A more adaptive field would automatically adjust coupling based on the rooms' behavior—strengthening coupling between rooms whose outputs are correlated and weakening it between rooms whose outputs are independent. This is analogous to Hebbian learning in neural networks.

**Fixed channel set.** The nine channels were derived empirically and may not be optimal for all agent configurations. A more general approach would allow agents to define their own channel sets, with the constraint that all rooms in a single field must share the same channels.

**Single-field assumption.** The current model assumes all rooms exist within a single shared field. For large agents with hundreds of rooms, this may become computationally expensive. A hierarchical field model—rooms within sub-fields, sub-fields within a meta-field—would provide better scalability while preserving the shared-medium semantics.

## 5.12 Conclusion

The AgentField demonstrates that within-agent coordination can be achieved without message passing. By representing the agent's internal state as a shared tensor field and rooms as views into this field, we eliminate the quadratic message overhead, the one-tick latency, and the synchronization complexity of message-passing architectures. The nine-channel representation captures the essential dimensions of room state, and the coupling matrix provides a clean mechanism for directed information flow.

The chirality state machine (exploring → locking → locked) provides a natural mechanism for phase transitions in room behavior, and the gap channel connects within-agent coordination to the collective inference framework. The side-channel operations (nod, smile, frown) demonstrate that even seemingly complex communicative acts reduce to simple matrix operations in the field model.

The physical analogy of rooms as standing waves in a resonance chamber is not merely illustrative—it provides the mathematical framework for analyzing the field's convergence properties, stability, and emergent behavior. The AgentField is, at its core, a physics-inspired architecture for within-agent coordination that trades the flexibility of message passing for the efficiency and analyzability of shared-state diffusion.

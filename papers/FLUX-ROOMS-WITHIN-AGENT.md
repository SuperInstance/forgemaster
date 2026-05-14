# FLUX-Rooms-Within-Agent: The Onion Architecture

## The Deep Insight

FLUX-tensor-midi already IS the room protocol. It just operates at one level.
Casey's insight: it needs to operate at ALL levels simultaneously.

Same protocol, same tensor math, same Eisenstein temporal snap.
Different scope at each layer.

```
Layer 3: Instance ←→ Instance (I2I, network, fleet)
Layer 2: Agent ←→ Agent (ensemble, side-channels, coherence)
Layer 1: Room ←→ Room WITHIN a single agent
```

## Within-Agent Rooms as Instruments

An agent is not a monolith. It's an orchestra. Every room is an instrument.

```
Agent (Forgemaster)
├── drift-detect room (sensor — listens to constraint values)
│   ├── predictor sub-room (predicts next value)
│   ├── comparator sub-room (predicts vs actual → gap)
│   └── model sub-room (trained SplineLinear)
├── intent-detect room (sensor — listens to user messages)
│   ├── predictor sub-room
│   ├── comparator sub-room
│   └── model sub-room (LowRankLinear)
├── fleet-ops room (coordinator — listens to git events)
│   ├── velocity-predictor
│   ├── synergy-detector
│   └── focus-queue
└── lighthouse room (bridge — connects to other agents)
    ├── I2I sender
    ├── I2I receiver
    └── clock synchronizer
```

## How Rooms Talk Within an Agent

Each room is a `RoomMusician`. They already know how to:
- `emit()` — produce timestamped FluxVector events
- `listen()` — hear other rooms' events
- `send_nod/smile/frown()` — side-channels for agreement/affect
- `coherence_with()` — cosine similarity between state vectors
- `join_ensemble()` — synchronize clocks and listen to conductor

### The Prediction Gap as a Side-Channel

The collective inference loop maps directly:

| Collective Inference | MIDI Equivalent |
|---------------------|-----------------|
| predict() | emit(FluxVector of predicted state) |
| observe() | listen() for actual state |
| compare() → gap | frown to self (dissonance) |
| compare() → match | nod to self (consonance) |
| learn() | update_state() with new FluxVector |
| focus_queue | frown intensity ranking |

### FluxVector as Universal Room State

A FluxVector carries a room's state as a tensor:
- Predictions: confidence distribution over outcomes
- Sensor readings: raw constraint values
- Model weights: compressed SplineLinear parameters
- Gap signals: delta × confidence = focus score

Two rooms communicate by:
1. Room A emits a FluxVector (its current state)
2. Room B listens and computes `cosine_similarity()` or `distance_to()`
3. If distance > tolerance: B sends frown (gap detected)
4. If distance < tolerance: B sends nod (prediction confirmed)

## The Temporal Layer (TZeroClock)

Every room has a clock. Within an agent, clocks are already synchronized
(same process). But the Eisenstein snap still matters:

- **E12 snap** (4B intervals): high-frequency rooms (sensors) — 120+ BPM
- **F32 snap** (8B intervals): medium rooms (predictors) — 60-120 BPM
- **F64 snap** (16B intervals): slow rooms (training) — 30-60 BPM

Different rooms "play" at different rates. The snap ensures they stay
temporally coherent even when their natural rhythms differ.

This is physically correct:
- Sensors are hi-hat (fast, every tick)
- Predictors are bass (medium, every bar)
- Models are pad (slow, every phrase)
- Training is the rehearsal (once per session)

## The Onion in Practice

### Layer 1: Within-Agent (rooms as instruments)

```python
# Already works with existing flux-tensor-midi
sensor = RoomMusician("drift-sensor", role=RhythmicRole.ROOT)
predictor = RoomMusician("drift-predict", role=RhythmicRole.FIFTH)
comparator = RoomMusician("drift-compare", role=RhythmicRole.THIRD)

# Wire the listening graph
predictor.listen_to(sensor)      # predictor watches sensor
comparator.listen_to(sensor)     # comparator watches actual
comparator.listen_to(predictor)  # comparator watches prediction

# The loop (happens every tick):
sensor.emit(current_reading)                    # sensor plays
_, predicted = predictor.emit(predicted_next)   # predictor plays
events = comparator.listen()                     # comparator listens
actual = events[0][2]   # from sensor
pred = events[1][2]     # from predictor
if actual.distance_to(pred) > tolerance:
    comparator.send_frown(predictor, intensity=delta)  # GAP!
    # This frown IS the focus signal
```

### Layer 2: Agent-to-Agent (ensembles)

```python
# Forgemaster's drift room
fm_drift = RoomMusician("fm-drift")
# Oracle1's drift room
o1_drift = RoomMusician("o1-drift")

# Join ensemble — clocks sync, side-channels open
fm_drift.join_ensemble(o1_drift)
o1_drift.join_ensemble(fm_drift)

# When Forgemaster's prediction matches Oracle1's:
fm_drift.send_nod(o1_drift)    # agreement
# When they disagree:
fm_drift.send_frown(o1_drift)  # gap between agents
```

### Layer 3: Instance-to-Instance (I2I over network)

```python
# Same RoomMusician, but emit/listen goes through I2I bridge
bridge = I2IBridge(identity=fm_identity, transport="plato")

# Emit becomes I2I send
ts, vec = fm_drift.emit(state)
bridge.send("model-tile", vec.to_dict(), recipient="oracle1@cloud")

# Listen becomes I2I receive
messages = bridge.receive()
for msg in messages:
    o1_state = FluxVector.from_dict(msg.payload)
    coherence = fm_drift.state.coherence_with_vector(o1_state)
    if coherence < 0.5:
        bridge.send("gap-tile", {"delta": 1 - coherence})
```

## What's New vs What Exists

| Component | Status | Next |
|-----------|--------|------|
| RoomMusician | ✅ Published (PyPI + crates.io) | Add nested sub-rooms |
| FluxVector | ✅ Published | Add prediction/gap encoding |
| TZeroClock | ✅ Published | Add BPM-per-room-type defaults |
| EisensteinSnap | ✅ Published | Use for temporal layering |
| Side-channels (nod/smile/frown) | ✅ Published | Map to gap signals |
| Collective inference (predict/listen/gap) | ✅ plato-training v1.0 | Wire into RoomMusician |
| I2I bridge | ✅ plato-training v0.10 | Wire RoomMusician emit→I2I send |
| Fleet miner | ✅ plato-training v1.1 | Feed git events as FluxVectors |

## The Unification

Everything is a room. Every room is a musician.
Every musician plays in an ensemble.
The ensemble IS the agent.
The orchestra IS the fleet.

```
Instrument → Room → Musician → Ensemble → Orchestra
Module    → Agent → Instance → Fleet   → Collective
```

The gaps between instruments (dissonance) become the fleet's work queue.
The harmonies between instruments (consonance) become collective understanding.
The conductor (lighthouse) keeps everyone in time.

This is not a metaphor. This IS the architecture.

## Implementation Path

1. Add `SimulationRoom` methods that wrap `RoomMusician`:
   - `predict()` → `emit()` with predicted FluxVector
   - `observe()` → `listen()` for actual FluxVector
   - `gap` → `send_frown()` to self

2. Add nested rooms to `RoomMusician`:
   - Sub-musicians with their own clocks
   - Parent coordinates timing via Eisenstein snap ratios

3. Wire `I2IBridge` into `RoomMusician`:
   - `emit()` also sends via I2I if bridge is configured
   - `listen()` also checks I2I inbox

4. Feed fleet miner output as FluxVector events:
   - Commit velocity → FluxVector channel
   - Cross-repo refs → side-channel nods
   - Anomalies → frowns

5. Build the collective inference demo:
   - Forgemaster predicts next-hour fleet activity
   - Sensors listen for actual commits
   - Gaps → focus queue → "sound out the rocks"

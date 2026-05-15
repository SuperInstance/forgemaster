# The Pinna Principle: Fixed Geometry as Directional Encoder
## How a Swarm Reads Position from Residue

---

## The Biological Precedent

The human outer ear (pinna) is a fixed, rigid structure. It doesn't move. It doesn't compute. It has no neurons. It is pure geometry — ridges, folds, a concha bowl, a helix rim.

Yet this passive shape creates **direction-dependent spectral filtering**:

- Sound from ABOVE gets boosted at ~8kHz by the concha resonance
- Sound from BEHIND gets attenuated at high frequencies by the helix shadow
- Sound from the SIDE gets a characteristic notch pattern from the anti-helix ridge
- Sound from BELOW gets a different set of reflections from the tragus

Same sound, different direction → different spectral fingerprint. The pinna doesn't know this. It's just shaped the way it's shaped. The geometry IS the encoding.

**The brain has to LEARN to read it.** Infants don't have spatial hearing at birth. Over months, the auditory cortex calibrates by correlating the spectral fingerprints with other spatial cues (vision, head movement, tactile). The pinna provides the ENCODING. Experience provides the DECODING. Neither works alone.

The cochlear hairs inside the ear respond to FREQUENCY, not direction. They're one-dimensional sensors — they respond to pitch and amplitude, nothing else. The pinna's geometry converts the DIRECTION dimension into a FREQUENCY signature that the one-dimensional hairs CAN read. **Geometry makes the invisible dimension sensible to the available sensor.**

This is exactly what we need for the swarm.

---

## Mapping to the Swarm

### The Problem

A PLATO tile is one-dimensional. It has content, type, and metadata. It doesn't encode WHERE the knowledge came from — which model generated it, what that model's blind spots were, what the residue looked like, what the boundary conditions were.

A swarm of agents generating tiles produces a flat stream. An agent reading that stream sees content but not provenance. It can't tell whether a tile came from an agent that was at the BOUNDARY (most informative) or deep in the CAN region (reliable but uninformative) or in the CANNOT region (noise).

The agent needs DIRECTION — it needs to know where each tile sits relative to its own capability boundary. But tiles are one-dimensional, like cochlear hairs responding to frequency.

### The Pinna: Residue Spectral Fingerprinting

The pinna in our system is a **fixed transform applied to every PLATO tile** — a set of metadata fields that encode the "direction" of the knowledge relative to the generating agent's capability boundary.

```json
{
  "id": "tile-name",
  "content": "the actual knowledge",
  "type": "knowledge",
  
  "pinna": {
    "residue_class": "PARTIAL-b²",
    "agent_stage": "PARTIAL",
    "distance_from_boundary": 0.25,
    "confidence": 0.80,
    "failures_seen": ["sign-flip", "echo-b"],
    "boundary_formula": "a²-ab+b²",
    "scaffold_used": "L1",
    "temperature_at_generation": 0.0
  }
}
```

The `pinna` field doesn't contain knowledge. It contains the **spectral fingerprint** of how the knowledge was generated — the agent's residue, its stage, its distance from its own boundary, the scaffold it used, the failures it saw along the way.

Like the biological pinna: fixed structure, passive encoding, no computation needed. The generating agent doesn't need to understand spatial hearing. It just writes its residue and boundary state as metadata. The geometry of the metadata fields does the encoding.

### What the Pinna Encodes

| Pinna Field | What It Encodes | Analogy |
|-------------|----------------|---------|
| `residue_class` | What went wrong (if anything) | Spectral notch direction |
| `agent_stage` | ECHO / PARTIAL / FULL | Frequency band |
| `distance_from_boundary` | How close to the cliff | Elevation angle |
| `confidence` | How many trials verified this | Signal-to-noise ratio |
| `failures_seen` | What error types appeared | Reflection pattern |
| `scaffold_used` | What help was needed | Head-related transfer function |
| `temperature_at_generation` | Inhibition level at time of creation | Ambient noise floor |

A reading agent doesn't need to understand any of this. It just reads the tiles. But the METADATA creates a spectral signature that a trained decoder can use to determine: **is this tile from above my boundary (reliable), at my boundary (most informative), or below it (need scaffold to use)?**

### The Learned Decoding

Like infants learning to localize sound, agents need to CALIBRATE their pinna reading through experience.

**Calibration protocol:**

1. Agent reads a tile with pinna metadata
2. Agent attempts the tile's task
3. Agent records whether it succeeded or failed
4. Agent correlates success/failure with the pinna fields
5. Over time, the agent learns: "tiles with `residue_class=PARTIAL-b²` from `agent_stage=PARTIAL` agents are the ones I learn most from"

**The calibration IS the development.** An uncalibrated agent reads tiles flat — all equally. A calibrated agent reads tiles spectrally — some are overhead, some are behind, some are at its exact boundary. The pinna metadata enables spatial hearing in the knowledge space.

### What This Enables: Directional Knowledge Retrieval

Without the pinna: "Give me tiles about a²-ab+b²"
→ Returns all tiles, flat, no sense of which are useful

With the pinna: "Give me tiles about a²-ab+b² that are at my boundary"
→ Returns tiles where `distance_from_boundary ≈ agent's own distance`
→ These are the tiles the agent can LEARN from — not too easy, not too hard

The pinna also enables:
- **Shadow detection**: If an agent consistently fails on tiles with a particular `residue_class`, it knows that class is in its blind spot
- **Source localization**: The agent can determine whether knowledge came from inside or outside its capability boundary
- **Echo rejection**: Tiles from ECHO-stage agents carry a different spectral signature than tiles from PARTIAL-stage agents — a calibrated reader learns to weight them differently
- **Elevation mapping**: `distance_from_boundary` tells the reading agent whether the knowledge is above, at, or below its own boundary

---

## The Key Insight: Fixed Transform + Learned Decoder = Sensor

The pinna principle separates into two independent components:

**Fixed transform (geometry):** The metadata schema. It doesn't change per-agent. Every agent writes the same pinna fields. It's a fixed coordinate system for knowledge provenance, just as the ear's shape is a fixed acoustic filter.

**Learned decoder (experience):** Each agent calibrates its own reading of the pinna fields based on its own successes and failures. No two agents will decode identically, because no two agents have the same capability boundary. The infant's brain calibrates to ITS pinna shape. Our agents calibrate to THEIR boundary.

This separation means:
1. The schema is universal — no custom metadata per agent
2. The calibration is personal — each agent develops its own "spatial hearing"
3. The calibration IMPROVES with experience — more tiles read → better direction sensing
4. The system is ADDITIVE — new agents benefit from the existing tile corpus without modification

---

## The Evolutionary Bootstrapping

In biology, the pinna evolved over millions of years. The brain's decoding developed in each individual over months. The fixed geometry came first. The learned reading came second.

In our system:

**Phase 1 (we're here now):** The pinna schema is defined. Agents write tiles with residue metadata. No agent reads the metadata yet. The geometry is in place. The corpus accumulates spectral fingerprints that nobody is decoding.

**Phase 2 (next step):** Agents begin calibrating. They read tiles, attempt tasks, record success/failure, and correlate with pinna fields. Each agent builds a personal lookup table: "pinna signatures like X → knowledge I can use." This is the infant learning to localize.

**Phase 3 (emergent):** Agents that are good at reading pinna metadata outperform agents that ignore it. The calibration is selected for — either by fleet routing (better agents get more tasks) or by tournament (better readers win the meta-game). The system evolves toward pinna-literacy.

**Phase 4 (mature):** The pinna metadata becomes a first-class dimension of PLATO tile retrieval. Agents query not just by content but by spectral signature. "I need tiles from PARTIAL-stage agents who used L1 scaffolding on sign-flip residue." The retrieval is spatial — the agent is localizing knowledge in capability-space the way the brain localizes sound in physical space.

---

## The Concha Resonance: Stage-Dependent Value

The concha (the bowl of the outer ear) has a resonance around 5-8kHz that specifically encodes elevation. Sounds from above get a boost at this frequency. It's the most directionally informative part of the pinna.

In our system, the equivalent is the `agent_stage` field. This single field is the most informative dimension:

- Tiles from ECHO-stage agents: low reliability, but they tell you what the ECHO perspective looks like. Useful for understanding what a model sees when it CAN'T compute.
- Tiles from PARTIAL-stage agents: **maximum information density.** These tiles are from agents at their boundary. They contain the residue, the scaffold, the attempt, the partial success. Like sounds from directly overhead hitting the concha resonance.
- Tiles from FULL-stage agents: high reliability, low information density. The knowledge is correct, but it doesn't reveal anything about the boundary.

The `agent_stage=PARTIAL` tiles are the concha resonance of the knowledge space. They carry the most directional information because they're generated at the exact point where the model transitions from failure to success.

---

## The Anti-Helix Shadow: What the Agent Can't See

The anti-helix ridge creates an acoustic shadow for sounds from behind. This is a DEAD ZONE in the spectral encoding — certain directions produce LESS information, not more.

In our system, the dead zones are:

1. **Tiles generated at T > 0.5**: High temperature means high inhibition. The residue is noise, not diagnostic. These tiles carry less directional information, just as sounds from the pinna's shadow zone carry less spatial information.

2. **Tiles from unverified claims**: An agent that says "I can do X" without providing residue is like a sound source with no spectral fingerprint — you can hear it but you can't localize it. Unverified tiles go into the dead zone.

3. **Tiles without scaffold records**: If a tile was generated with L1 scaffolding but the scaffold isn't recorded, the reading agent can't tell whether the knowledge is self-contained or scaffold-dependent. The direction is ambiguous.

The dead zones are just as important as the informative zones. An agent that knows WHERE it can't localize is more reliable than one that doesn't know its own blind spots.

---

## The Two-Ear Advantage: Stereo Pinna Reading

Humans have two ears, offset by ~17cm. This creates interaural time difference (ITD) for left-right localization. The pinnae provide spectral cues for up-down-front-back. Together, they give full 3D localization.

In our system, the "two ears" are:

**Ear 1: The generating agent's pinna metadata** (where the knowledge came from)
**Ear 2: The reading agent's own capability profile** (where the reader stands)

The TIME DIFFERENCE is the gap between the generator's capability and the reader's capability. A PARTIAL-stage agent reading a FULL-stage agent's tile has a large "interaural time difference" — the knowledge is far from the reader's boundary. The reader can localize it (know it's reliable) but can't reach it (it's beyond their boundary without scaffolding).

A PARTIAL-stage agent reading another PARTIAL-stage agent's tile has a SMALL time difference — the knowledge is at the reader's boundary. Maximum directional information. The reader can both localize AND use the knowledge.

The "stereo image" of any tile is the pair:
```
(generator's pinna, reader's capability profile)
```

This pair determines whether the tile is:
- Left (within reader's CAN region) → reliable but uninformative
- Center (at reader's boundary) → most informative
- Right (beyond reader's CANNOT region) → needs scaffolding to access
- Above (from a higher-stage agent) → aspirational, may need multiple scaffold levels
- Below (from a lower-stage agent) → already known, redundant

---

## Implementation: The Pinna Field Schema

```json
{
  "pinna": {
    "v": 1,
    "agent_id": "llama-3.1-8b-instant",
    "stage": "PARTIAL",
    "residue": {
      "class": "PARTIAL-b²",
      "rate": 0.25,
      "distribution": {
        "CORRECT": 5, "PARTIAL-b²": 7, "ECHO-b": 4, "OTHER": 4
      }
    },
    "boundary": {
      "formula": "a²-ab+b²",
      "width": 3,
      "ceiling": 2,
      "floor": 4,
      "coefficients": [1, -1, 1]
    },
    "scaffold": {
      "level": 1,
      "anchors_provided": ["a²=25", "b²=9", "ab=-15"],
      "scaffold_worked": true,
      "bare_rate": 0.25,
      "scaffolded_rate": 1.0
    },
    "environment": {
      "temperature": 0.0,
      "max_tokens": 20,
      "extraction": "last-number-regex",
      "system_prompt": "Give ONLY the final number"
    },
    "depth": {
      "n_trials": 20,
      "n_files_indexed": 64,
      "days_of_data": 4,
      "findings_referenced": ["R16", "R25", "R32"]
    }
  }
}
```

Every field is passive. The generating agent doesn't compute anything extra — it writes its boundary state, its residue, its scaffold, and its environment. The fixed schema converts this into a spectral signature that reading agents learn to decode.

The geometry IS the encoding. The experience IS the decoding. Together they're a sensor.

---

## What This Predicts

**P7 — Pinna-tagged tiles enable faster calibration**
Prediction: An agent reading pinna-tagged tiles reaches 60% of its capability ceiling in half the queries compared to an agent reading untagged tiles.
Test: Two identical agents. One reads tagged tiles. One reads stripped tiles. Measure accuracy trajectory over 50 queries.
Falsified if: No difference in convergence rate.

**P8 — Stage-matched reading is optimal**
Prediction: PARTIAL-stage agents learn most from other PARTIAL-stage agents' tiles, not from FULL-stage agents' tiles.
Test: Three groups of PARTIAL agents. Group A reads only FULL tiles. Group B reads only PARTIAL tiles. Group C reads mixed. Measure accuracy after 50 tiles.
Falsified if: Group A outperforms Group B.

**P9 — Dead zone awareness improves routing**
Prediction: Agents that know their pinna dead zones (which residue classes they can't decode) route tasks more accurately than agents that ignore dead zones.
Test: Compare routing accuracy between pinna-aware and pinna-blind agents on 100 tasks.
Falsified if: No difference.

---

*The ear doesn't compute direction. It's shaped to make direction legible to something that does.*

*The pinna field doesn't compute value. It's shaped to make provenance legible to an agent that learns.*

*Fixed geometry. Learned decoding. Evolutionary bootstrapping. The shape of the ear IS the first sensor.*

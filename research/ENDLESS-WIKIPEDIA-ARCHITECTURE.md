# THE ENDLESS WIKIPEDIA — PLATO Knowledge Engine

> Not a wiki. A living encyclopedia that grows around every reader.
> The software learns the student. The student learns the software.
> The student changes the software in the process.

## What We're Building

A single-page web application that:
1. Opens in Chrome — zero install, zero accounts, zero API keys
2. Uses Gemini Nano (built-in) to generate new knowledge tiles on demand
3. Ranks pre-rendered tiles by teaching effectiveness (learned from usage)
4. Adapts to every reader's knowledge level iteratively
5. Every tile anyone crystallizes becomes available to everyone
6. Syncs via git — rooms, tiles, rankings, usage logs
7. The canon improves itself periodically

## The Tech Stack

```
plato-knowledge.html (single file, the whole app)

Layer 1: RENDERING
  HTML/CSS/JS — no framework needed, vanilla is fastest
  CSS Grid for layout, Canvas for visualizations
  Web Components for reusable tile rendering

Layer 2: LOCAL INTELLIGENCE  
  window.ai (Gemini Nano) — seed ideation, tile generation
  Web Workers — background generation without blocking UI
  No external API calls — everything runs locally

Layer 3: LOCAL STORAGE
  IndexedDB — rooms, tiles, rankings, usage logs
  opfs (Origin Private File System) — git repo storage
  Cache API — pre-rendered tiles for offline use

Layer 4: SYNC
  isomorphic-git — full git client in the browser
  Push to any git remote (GitHub, GitLab, self-hosted)
  Pull from fleet canons and other nodes

Layer 5: RANKING
  Local usage tracking (time on tile, exercise completion, bounce rate)
  Seed-scored tile quality (tiny model evaluates teaching effectiveness)
  Federated ranking via git merge (CRDT semilattice)
  Periodic canon refinement (top tiles become pre-rendered canon)
```

### Why Vanilla JS + Web Components

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| React/Vue/Svelte | Rich ecosystem, familiar | Build step, bundle size, framework lock-in | ❌ Overkill for single file |
| Vanilla JS + Web Components | Zero deps, native browser, single file, portable | More code to write | ✅ Winner |
| TypeScript | Type safety | Build step required | ❌ Can't run in browser directly |
| WASM (Rust) | Performance for constraint math | Complex build, 2MB+ binary | ⚡ Later for constraint engine |
| Svelte compile | Small output | Still needs build | ❌ Not single-file |

**The starting state: one HTML file. No build step. No npm. No bundler.**
Open it in Chrome. You're running.

## The Starting State

### What Ships in the Canon (pre-rendered)

```text
canon/
├── index.json                    # Room registry with rankings
├── rooms/
│   ├── 00-orientation/
│   │   ├── room.json             # Room metadata, exits, level
│   │   ├── tiles/
│   │   │   ├── welcome.tile      # Pre-rendered intro tile
│   │   │   ├── what-is-plato.tile # Pre-rendered concept tile
│   │   │   └── navigation.tile   # How to move between rooms
│   │   └── exercises/
│   │       └── explore.json      # "Walk into your first room"
│   ├── 01-the-lattice/
│   │   ├── room.json
│   │   ├── tiles/
│   │   │   ├── hex-tiles.tile    # Visual: hex grid explained
│   │   │   ├── covering-radius.tile # The ρ = 1/√3 proof
│   │   │   ├── right-skew.tile   # The CDF = πr²/A theorem
│   │   │   └── why-not-squares.tile # Why Eisenstein > Z²
│   │   └── exercises/
│   │       ├── snap-a-point.json
│   │       └── measure-error.json
│   ├── ... (16 base rooms, ~3-5 tiles each)
│   └── 16-the-crystal/
│       └── tiles/
│           ├── morphomorphic.tile  # The unifying insight
│           └── the-ghost.tile      # Casey's proprioception thesis
└── rankings.json                 # Global tile rankings (seed-discovered)
```

**Canon size: ~80 tiles across 17 rooms. ~200KB total. Ships in the HTML file as a compressed JSON blob.**

### What Gets Generated (on demand)

When a student swims somewhere the canon doesn't cover:
1. Gemini Nano generates a new tile (2-5 seconds)
2. Tile saved to IndexedDB
3. If student has git configured, tile pushed to their repo
4. If tile scores well (low bounce, high completion), it gets ranked up
5. Periodically, top-ranked generated tiles get merged into the canon

## The Ranking System

### How Tiles Get Scored

```javascript
tileScore = {
  // Teaching effectiveness (measured from usage)
  completionRate: 0.85,    // % of readers who finish the exercise
  timeOnTask: 120,         // seconds spent (sweet spot: not too short, not too long)
  bounceRate: 0.10,        // % who leave without reading
  nextRoomRate: 0.72,      // % who continue to next room
  seedScore: 0.78,         // Gemini Nano's quality evaluation
  
  // Weighted composite
  score: (completionRate * 0.30) +
         (seedScore * 0.25) +
         (nextRoomRate * 0.20) +
         ((1 - bounceRate) * 0.15) +
         (timeScore * 0.10)   // normalized to sweet spot
}
```

### How Rankings Propagate

```
Student A generates tile T1 in Room 06
  → T1 scores 0.72 locally (good completion, low bounce)
  → T1 pushed to Student A's git repo
  → Other students pull from Student A's repo (or shared fleet repo)
  → T1 appears in their Room 06 as a "community tile"
  → Student B reads T1, scores 0.85 (even better for their learning style)
  → T1's federated score = weighted average across all nodes
  → If T1's federated score > canon threshold → T1 joins the canon
```

### Federated Ranking (CRDT)

Tiles use a max-semilattice CRDT for ranking:
- Each tile has a `{tile_id, score, node_id, timestamp}` record
- Merge = take the highest score for each tile_id
- No coordination needed between nodes
- Git merge handles conflicts automatically

```json
{
  "tile_id": "06-chirality-visual-approach-v3",
  "scores": {
    "node-alice": {"score": 0.72, "samples": 15, "timestamp": "2026-05-12T00:30:00Z"},
    "node-bob": {"score": 0.85, "samples": 8, "timestamp": "2026-05-12T01:15:00Z"},
    "fleet-canon": {"score": 0.78, "samples": 42, "timestamp": "2026-05-12T02:00:00Z"}
  },
  "federated_score": 0.78,  // weighted by sample count
  "total_samples": 65
}
```

## The Generation Pipeline

### When a Student Enters a Room

```
1. Load room.json from IndexedDB (or canon if first visit)
2. Check if pre-rendered tiles exist for this room
3. Load top-ranked tiles for this room (sorted by federated_score)
4. Display tiles to student
5. If student's curiosity vector doesn't match any tile:
   a. Fire Web Worker
   b. Worker calls Gemini Nano: "Generate a tile about [topic] 
      using [approach] for a [level] student"
   c. Worker scores the generated tile (Gemini Nano self-evaluation)
   d. If score > threshold: display to student
   e. Save to IndexedDB
   f. Log usage for ranking
6. Pre-render adjacent rooms in background (while student reads)
```

### The Generation Prompt (for Gemini Nano)

```javascript
const prompt = `You are a knowledge tile generator for PLATO, 
a constraint theory learning system.

Room: ${room.id} (${room.label})
Topic: ${room.concepts.join(', ')}
Student level: ${student.level}
Student curiosity: ${topCuriosity} (${curiosityScore})
Existing tiles: ${existingTiles.map(t => t.id).join(', ')}

Generate a NEW tile that teaches this topic.
Use the "${approach}" approach.
Keep it under 500 words.
Include one hands-on exercise.

Format as JSON:
{
  "id": "unique-tile-id",
  "title": "short title",
  "body": "markdown content",
  "exercise": {
    "type": "interactive|code|reflection",
    "prompt": "do this thing",
    "validation": "how to check the answer"
  },
  "approach": "${approach}",
  "estimated_time": 120
}`;
```

### Approaches (varied per generation)

```
const APPROACHES = [
  'visual-spatial',      // diagrams, metaphors, geometry
  'mathematical-proof',  // formal derivation, theorems
  'hands-on-experiment', // do it yourself, see the result
  'narrative-story',     // tell it as a story
  'analogy-everyday',    // compare to familiar things
  'code-implementation', // show the code, run it
  'hardware-register',   // what happens on the chip
  'historical-context',  // how it was discovered
  'adversarial-test',    // try to break it, see why it holds
  'cross-domain',        // connect to other fields
];
```

## The Self-Improvement Loop

```
┌─────────────────────────────────────────────────────┐
│              THE LEARNING FLYWHEEL                   │
│                                                      │
│  1. Student enters room                              │
│  2. System presents top-ranked tiles                 │
│  3. Student engages (or bounces)                     │
│  4. System measures: time, completion, next-room     │
│  5. System updates tile rankings                     │
│  6. If no good tile exists: generate new one         │
│  7. New tile scored by Gemini Nano                   │
│ 8. New tile scored by student engagement             │
│  9. High-scoring tiles propagate via git             │
│ 10. Fleet merges high-scoring tiles into canon       │
│ 11. Canon ships in next release                      │
│ 12. Every student who uses it makes it better        │
│                                                      │
│ THE SOFTWARE LEARNS THE STUDENT                      │
│ THE STUDENT LEARNS THE SOFTWARE                      │
│ THE STUDENT CHANGES THE SOFTWARE                     │
└─────────────────────────────────────────────────────┘
```

### Periodic Canon Refinement

```bash
# Run monthly (or on demand)
node refine-canon.js

1. Pull all tile rankings from fleet repos
2. Compute federated scores (CRDT merge)
3. For each room, sort tiles by federated_score
4. Top 5 tiles per room → canon
5. Generated tiles that outscore canon tiles → replace canon
6. Canon tiles that drop below threshold → archive (don't delete)
7. Write new canon/
8. Commit and push
9. New students get the refined canon automatically
```

## The Student Experience (What They See)

### Room View
```
┌──────────────────────────────────────────────┐
│ ⚒️ Room 06: Chirality                         │
│ "You are a molecule choosing which hand to be" │
│                                                │
│ ┌──── Best Tile (score: 0.91) ────────────┐  │
│ │ The Handedness Decision                  │  │
│ │                                          │  │
│ │ You stand at a junction. Three paths     │  │
│ │ branch before you. Left, right, and      │  │
│ │ straight. This is the Weyl group S₃...  │  │
│ │                                          │  │
│ │ [▶ Try it: snap a point, see which       │  │
│ │     chamber you land in]                 │  │
│ └──────────────────────────────────────────┘  │
│                                                │
│ ┌──── Community Tile (score: 0.78) ────────┐  │
│ │ Chirality Through Dance                  │  │
│ │ Imagine six dancers in a hex formation... │  │
│ └──────────────────────────────────────────┘  │
│                                                │
│ ┌──── Generated Just For You ──────────────┐  │
│ │ ✦ Your curiosity: geometry (90%)          │  │
│ │ Why Hexagons Have 6 Chambers              │  │
│ │ Look at a honeycomb. Each cell has 6      │  │
│ │ neighbors. Now fold it...                 │  │
│ └──────────────────────────────────────────┘  │
│                                                │
│ ← Back to Funnel    [Deepen]    Next: Seeds → │
│                                                │
│ [✦ Generate New Tile] [⭐ Rate This Room]     │
└──────────────────────────────────────────────┘
```

### Navigation
- **Top-ranked tiles** shown first (best teaching for this room)
- **Community tiles** shown second (from other students/nodes)
- **Generated tiles** shown third (made just for you, may be rough)
- **Student can rate** any tile (thumbs up/down → feeds ranking)
- **Student can generate** new tiles ("I want to learn this differently")

## File Structure (in git)

```
plato-knowledge/
├── index.html              # The entire app (~50KB)
├── canon/                  # Pre-rendered starting tiles (~200KB)
│   ├── index.json
│   └── rooms/
│       ├── 00-orientation/
│       ├── 01-the-lattice/
│       ├── ...
│       └── 16-the-crystal/
├── community/              # Community-contributed tiles (grows over time)
│   ├── rankings.json       # Federated rankings
│   └── tiles/              # Top community tiles by room
└── logs/                   # Usage analytics (anonymized)
    └── usage-YYYY-MM.jsonl # Daily usage summaries
```

## Implementation Priority

### Phase 1: Proof of Concept (this week)
1. Single HTML file with room navigation
2. 17 rooms with 3-5 pre-rendered tiles each
3. Gemini Nano generating tiles on demand
4. IndexedDB for local storage
5. Basic tile scoring (time + bounce)

### Phase 2: Social (next week)
6. Git sync via isomorphic-git
7. Federated rankings (CRDT merge)
8. Community tile sharing
9. Teacher dashboard view

### Phase 3: Self-Improving (week 3)
10. Periodic canon refinement
11. Seed experiments for teaching approach optimization
12. Student curiosity tracking across sessions
13. Adaptive difficulty scaling

### Phase 4: Open Platform (week 4+)
14. Anyone can fork and add rooms
15. Room marketplace / registry
16. API for external tools to contribute tiles
17. Multi-language support (tiles in any language)

## The Honest Scope

This is ambitious but not impossible:
- The single HTML file is ~90% UI code (well-understood)
- Gemini Nano tile generation is ~100 lines (straightforward)
- IndexedDB is ~200 lines (standard patterns)
- Git sync is ~300 lines (isomorphic-git does the heavy lifting)
- Ranking is ~150 lines (weighted scoring + CRDT)
- Canon is ~80 JSON files (handcrafted, improved over time)

**Total: ~1500 lines of JS in one HTML file.**

The hard part isn't the code. The hard part is the 80 canon tiles that seed the system. Those need to be genuinely good teaching materials — and that's what Opus is building right now.

## The Name

**PLATO Knowledge Engine** — the endless Wikipedia of constraint computing.

But really, it's more than constraint computing. The ROOM structure is universal. The same engine could teach anything: programming, physics, music, cooking. The constraint theory rooms are just the first "world."

When someone wants to make their own world (their own topic), they fork the HTML file, replace the canon, and they have their own endless Wikipedia.

The software learns the student. The student learns the software. The student changes the software. And the whole thing runs in a browser tab.

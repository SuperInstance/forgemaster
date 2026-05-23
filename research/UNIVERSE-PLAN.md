# Cocapn Universe — Design Plan
### Transforming 7 isolated HTML demos into one living system

---

## The Problem Statement

Seven demos. Seven tabs. A user opens drift-race.html, watches numbers, closes it,
opens the next tab. They never feel the *system*. They never see that hex-snap
**is** the engine inside safe-arm, or that fleet-topology's consensus algorithm
**is** the Potts model visualized in constraint-funnel.

The current hub page draws connection lines between cards — but those lines are
cosmetic. Data doesn't flow. The system isn't alive. Fix that, and everything else
follows.

---

## Narrative Arc — The Three-Act Journey

A visitor should experience a complete intellectual arc, not a feature checklist.

### Act I: The Problem (2 minutes)
> *"Floating point is broken and you probably don't know it."*

**Entry point: Drift Race.** No preamble. Immediate visceral impact. Watch two dots
on a circular track. They start together. By lap 3, Float32 is visibly spiraling
outward. By lap 20, it's off the track entirely. The E12 dot is still on the line,
pixel-perfect. A counter shows `Float32 drift: 4.7mm`. Boom. You've understood the
core problem.

**Transition:** A subtle banner fades in: "The Eisenstein lattice prevents this.
→ See how." User clicks. They land on Hex Snap.

### Act II: The Solution (3 minutes)
> *"A 60-degree symmetric lattice catches every rounding error before it compounds."*

**Hex Snap.** The user discovers they can click anywhere on the plane and watch the
point snap to the nearest Eisenstein lattice vertex. The snap distance is shown. The
Weyl sector is highlighted. The user intuitively grasps: floating point is a grid
that doesn't match reality; E12 is a grid that does.

**Transition:** "Now give it a body." → Safe Arm.

### Act III: The Machine (5 minutes)
> *"UNSAFE: crashes. SAFE: never crashes. Same task. Different arithmetic."*

**Safe Arm.** Side-by-side arms. One uses unconstrained float arithmetic for joint
angles. The other snaps every angle to an Eisenstein lattice point before applying.
The UNSAFE arm drifts into obstacles. The SAFE arm stops. Always. The user clicks
"Load in FLUX VM" and sees the constraint program that makes this happen.

**From here, three branches:**

- *Engineering track:* FLUX VM → understand the bytecode
- *Systems track:* Fleet Topology → scale to 15 coordinating agents
- *Theory track:* Constraint Funnel → understand the thermodynamics

### Act IV: The Depth (optional, non-linear)
> *"How deep does it go?"*

The user realizes: the Potts model temperature in Constraint Funnel is literally the
same parameter as the Fleet consensus threshold. The Memory Palace indexes every
concept we've just experienced. The hub page reveals itself as a live control room
where all 7 demos are simultaneously active.

---

## The Wow Moments — Specific "Holy Shit" Events

These are concrete, implementable moments that make someone stop scrolling.

### WOW-1: Live Drift Feed to Fleet
When Drift Race is running in any browser tab, Fleet Topology's nodes show a live
"drift health" indicator. Each fleet node's signal strength fluctuates based on the
current Float32 accumulated error. Open both tabs side by side: drift goes up,
fleet nodes turn yellow/red in real time. **This is the system being alive.**

### WOW-2: "Compile & Load" — VM to Arm
In FLUX VM, there's a program selector. One option: "safe-arm-control.flux". The
user hits Run. In Safe Arm (open in another tab), the arm *actually moves* according
to the VM's execution. The arm pose updates at each STEP opcode. The user can edit
the FLUX program and watch the arm respond. **This is a live cross-demo actuator.**

### WOW-3: Temperature Sync — Funnel to Fleet
The Constraint Funnel's temperature slider broadcasts to Fleet Topology. As
temperature increases (system more disordered), Fleet consensus becomes harder —
more messages required, Betti number spikes, holonomy violations increase. The user
moves one slider and watches two different visualizations respond simultaneously.
**This makes the abstract thermodynamic model physically concrete.**

### WOW-4: The Control Room
A new page: `control-room.html`. Seven miniature live iframes, each 280×200px,
arranged in the exact topology of the hub connection graph. Data pulses flow as
animated particles along the connection lines — but these particles carry *real data*
(lap count, drift mm, VM program counter, arm angle, fleet consensus state).
**It looks like a real distributed system dashboard.**

### WOW-5: Constraint Sonification
Every Eisenstein snap event produces a tone. The Weyl sector maps to a pentatonic
scale position (6 sectors → 6 notes). Drift accumulation creates a slow beating
interference pattern in the audio. Fleet consensus produces a chord resolution.
Arm violation triggers a sharp dissonant sound, arm safe operation produces smooth
arpeggios. **Close your eyes and you can hear the constraint system working.**

### WOW-6: The Cinematic Landing
First 5 seconds: full-screen black. A single bright point. Then a hexagonal lattice
blooms outward from it, Eisenstein-symmetric, filling the screen. Voronoi cells pulse.
Then — points appear and start drifting, spiraling away from their home cells.
Then — snap events begin, catching the drifts, pulling points back. The screen reads:

```
  F L O A T I N G   P O I N T   I S   B R O K E N

  [ Enter the Universe ]
```

Total time: 4 seconds. No text before that line. No explanation needed.

---

## Visual Cohesion — The Design System

### Current State
The demos are visually close but inconsistent:
- `drift-race.html`: `#0a0a1a` background, `#00d4ff` E12 accent
- `safe-arm.html`: `#0d1117` background, `#58a6ff` accent
- `flux-vm.html`: CSS variables (`--bg`, `--accent`) — best structured
- `fleet-topology.html`: `#0d1117` background, `#58a6ff` accent
- `constraint-funnel.html`: unique purple gradient approach

### The Unified Token Set
All demos adopt these CSS custom properties via `core/design-system.css`:

```css
:root {
  /* Backgrounds — depth layers */
  --bg-0:      #06060f;   /* void / deepest */
  --bg-1:      #080810;   /* canvas background */
  --bg-2:      #0d1117;   /* panel background */
  --bg-3:      #161b22;   /* card background */
  --bg-4:      #21262d;   /* elevated surface */

  /* Borders */
  --border-0:  #1a1a2e;
  --border-1:  #30363d;

  /* Semantic accent colors — the 7 demo identities */
  --drift:     #f85149;   /* Float32 error — red/danger */
  --lattice:   #00d4ff;   /* Eisenstein lattice — cyan */
  --funnel:    #a855f7;   /* Potts model — purple */
  --arm:       #3fb950;   /* Safe arm — green */
  --vm:        #58a6ff;   /* FLUX VM — blue */
  --fleet:     #f59e0b;   /* Fleet — amber */
  --memory:    #7c5cfc;   /* Memory palace — violet */

  /* Typography */
  --font-ui:   'SF Pro Display', 'Segoe UI', system-ui, sans-serif;
  --font-mono: 'SF Mono', 'Cascadia Code', 'Fira Code', monospace;

  /* Motion */
  --ease-snap:    cubic-bezier(0.22, 1, 0.36, 1);   /* constraint snap feel */
  --ease-drift:   cubic-bezier(0.4, 0, 1, 1);        /* drift divergence feel */
  --ease-resolve: cubic-bezier(0, 0, 0.2, 1);        /* consensus resolution */
}
```

### Shared Visual Grammar

**The Eisenstein Lattice Background:** Every demo page uses the same animated
lattice background from `core/design-system.js`. Parameters differ (scale, opacity,
color) but the geometry is identical: hexagonal close-packing, 60° symmetry,
√3 aspect ratio. When a constraint snap occurs in any demo, the background lattice
in *all* open demos briefly pulses — a subtle shared heartbeat.

**The Particle Language:**
- Cyan flowing particles: lattice-constrained data (good state)
- Red particles with wobble: floating point drift (bad state)
- Amber branching particles: consensus messages (fleet protocol)
- Violet slow-moving particles: memory/knowledge traversal

**Typography Scale:**
- Landing: 72px display, wide tracking, thin weight
- Demo titles: 22px semibold, 2px tracking
- Metrics: 28px monospace, tabular nums, color-coded
- Body/labels: 12px, #8b949e muted
- Tags/badges: 10px uppercase, 3px tracking

**The Glow Language:**
- Exact constraint satisfaction: `box-shadow: 0 0 20px var(--lattice)60`
- Constraint violation: `box-shadow: 0 0 20px var(--drift)80, 0 0 40px var(--drift)30`
- Active computation: `box-shadow: 0 0 12px var(--vm)40` pulsing

---

## Cross-Demo Data Flow Architecture

### The Event Bus: `core/event-bus.js`

```javascript
// BroadcastChannel — zero latency, same origin, no server required
const COCAPN_BUS = new BroadcastChannel('cocapn-universe');

// Message schema
// Every message has: { type, source, ts, payload }
// Types:
//   drift:lap     { lap, float32_error_mm, e12_error_mm }
//   snap:event    { sector, distance, coords: {a, b} }
//   arm:pose      { angles: [float], lattice_coords: [{a,b}] }
//   arm:violation { joint, angle, obstacle }
//   vm:step       { pc, opcode, stack, registers }
//   vm:output     { type, value }
//   fleet:state   { consensus_count, betti, holonomy_violations, node_states }
//   funnel:temp   { temperature, phase, sigma }
//   memory:visit  { tile_id, domain, coords: {x,y} }
```

Each demo subscribes to the messages relevant to it and broadcasts its own state.
The bus is purely passive — demos can ignore messages they don't care about.
No demo is required to receive messages; the architecture is additive.

### Concrete Wiring Table

| From            | Event                | To               | Effect                                          |
|-----------------|----------------------|------------------|-------------------------------------------------|
| Drift Race      | `drift:lap`          | Fleet Topology   | Node signal strength = f(float32_error_mm)      |
| Drift Race      | `drift:lap`          | Control Room     | Live drift counter in hub overview              |
| Hex Snap        | `snap:event`         | All demos        | Lattice background pulse + audio tone           |
| Hex Snap        | `snap:event`         | Safe Arm         | Arm joint highlight — "this is what snapped"    |
| FLUX VM         | `vm:output`          | Safe Arm         | Arm executes output as movement command         |
| FLUX VM         | `vm:step`            | Control Room     | Program counter display in hub mini-panel       |
| Safe Arm        | `arm:pose`           | FLUX VM          | "Import current pose" button loads registers    |
| Safe Arm        | `arm:violation`      | Fleet Topology   | Adds a "red node event" to fleet event log      |
| Constraint Funnel | `funnel:temp`      | Fleet Topology   | Temperature → consensus difficulty multiplier   |
| Constraint Funnel | `funnel:phase`     | Drift Race       | Phase → Float32 noise amplitude                 |
| Fleet Topology  | `fleet:state`        | Memory Palace    | Consensus count → highlight active domain tiles |
| Memory Palace   | `memory:visit`       | Hub              | Visited tile glows on hub connection graph      |

### Implementation Notes

BroadcastChannel is supported in all modern browsers (Chrome 54+, Firefox 38+,
Safari 15.4+). No polyfill needed. Zero dependencies. No server. Works with
`file://` protocol in Chromium-based browsers when flags are set, but best served
from `localhost` or a static server.

For the Control Room iframe approach: use `postMessage` for parent→iframe
communication (BroadcastChannel is accessible inside iframes from same origin).

---

## New Pages & Files

### `/index.html` — The Cinematic Landing

**Storyboard:**

```
[0.0s] Black screen.
[0.5s] A single white hexagonal point appears at center. Soft hum begins.
[1.0s] Six neighbors bloom outward. The lattice grows like crystal formation.
       Sound: glass harmonic, rising.
[2.0s] The lattice fills the screen. 50 random points are placed on it.
       They begin to drift — slowly spiraling outward, leaving their home cells.
       Sound: subtle dissonance building.
[3.0s] Constraint snap events begin. Points are pulled back to lattice.
       Each snap: a bright cyan pulse. A clear musical tone.
       Sound: pentatonic snaps over the dissonance.
[4.0s] Text fades in, letter by letter, terminal-style:

         FLOATING POINT IS BROKEN

[5.5s] Second line appears:
         Eisenstein integers fix it.

[6.5s] The lattice transforms — 7 bright nodes bloom at the positions
       corresponding to the 7 demo cards. Connection lines draw themselves.
       The hub map materializes from the landing animation.

[7.5s] CTA appears: [ Enter the Universe ]  [ Start Guided Tour ]
```

**Tech:** Pure Canvas 2D + Web Audio API. No libraries. ~300 lines.

---

### `/hub.html` — The Living Map (upgrade of simulators/index.html)

Additions over the current version:

1. **Live status indicators** on each node card: a small colored dot showing
   whether that demo is currently open in another tab (via BroadcastChannel ping).
   Green = active, dim = inactive.

2. **Live data readouts** on connection lines: the animated pulse particles now
   show actual values (e.g., the drift→fleet connection shows `4.7mm` floating
   alongside the traveling pulse dot).

3. **"Open Control Room"** button: launches control-room.html.

4. **Tour Mode button**: starts the guided tour (see below).

---

### `/control-room.html` — The Dashboard

A 3×3 grid layout of live miniature views. Each cell is either:
- An `<iframe>` loading the actual demo (iframes can be pointer-events:none for
  a "watch only" mode, or interactive)
- A canvas thumbnail rendering a simplified version of each demo's current state

The connection graph overlays the grid with animated particle streams carrying
the live bus values.

**Layout sketch:**
```
┌─────────────────────────────────────────────────┐
│  COCAPN CONTROL ROOM          [TOUR] [FULLSCREEN]│
├───────────┬───────────┬───────────┬──────────────┤
│ Drift Race│  Hex Snap │  Funnel   │  STATS       │
│  [LIVE]   │  [LIVE]   │  [LIVE]   │  7 Demos     │
│           │     ↕     │           │  10 Channels │
│     ←─────┼───────────┼─────→     │  E12 Core    │
│ Safe Arm  │           │  Fleet    │              │
│  [LIVE]   │   HUB MAP │  [LIVE]   │  BUS TRAFFIC │
│           │  (center) │           │  [sparkline] │
│     ←─────┼───────────┼─────→     │              │
│ FLUX VM   │  Memory   │           │              │
│  [LIVE]   │  Palace   │           │              │
│           │  [LIVE]   │           │              │
└───────────┴───────────┴───────────┴──────────────┘
```

---

### `/core/` — Shared Modules

#### `core/eisenstein.js`
The mathematical heart. Currently every demo reimplements this independently.
Extract the shared E12 arithmetic into one module:

```javascript
// core/eisenstein.js
export const SQ3 = Math.sqrt(3);
export const ω = { re: -0.5, im: SQ3/2 };  // primitive 6th root of unity

export function e12_snap(x, y, scale) { ... }
export function e12_distance(ax, ay, bx, by) { ... }
export function weyl_sector(a, b) { ... }  // returns 0-5
export function lattice_to_screen(a, b, scale, cx, cy) { ... }
export function screen_to_lattice(x, y, scale, cx, cy) { ... }
export function e12_norm(a, b) { ... }
export function e12_add(a1, b1, a2, b2) { ... }
export function e12_multiply(a1, b1, a2, b2) { ... }  // Z[ω] multiplication
```

All 7 demos import from this module. The math is identical everywhere. This also
makes the system auditable: prove the math once, trust it everywhere.

#### `core/event-bus.js`
```javascript
// core/event-bus.js
const CHANNEL = 'cocapn-universe';

export function broadcast(type, payload) {
  const bc = new BroadcastChannel(CHANNEL);
  bc.postMessage({ type, source: document.title, ts: Date.now(), payload });
  bc.close();
}

export function subscribe(handler) {
  const bc = new BroadcastChannel(CHANNEL);
  bc.onmessage = (e) => handler(e.data);
  return () => bc.close();  // returns unsubscribe function
}

// Typed helpers (autocomplete-friendly)
export const emit = {
  driftLap: (lap, f32mm, e12mm) => broadcast('drift:lap', { lap, float32_error_mm: f32mm, e12_error_mm: e12mm }),
  snapEvent: (sector, dist, a, b) => broadcast('snap:event', { sector, distance: dist, coords: {a, b} }),
  armPose: (angles, lattice_coords) => broadcast('arm:pose', { angles, lattice_coords }),
  armViolation: (joint, angle, obstacle) => broadcast('arm:violation', { joint, angle, obstacle }),
  vmStep: (pc, opcode, stack, regs) => broadcast('vm:step', { pc, opcode, stack, registers: regs }),
  fleetState: (count, betti, violations, nodes) => broadcast('fleet:state', { consensus_count: count, betti, holonomy_violations: violations, node_states: nodes }),
  funnelTemp: (temperature, phase, sigma) => broadcast('funnel:temp', { temperature, phase, sigma }),
  memoryVisit: (tile_id, domain, x, y) => broadcast('memory:visit', { tile_id, domain, coords: {x, y} }),
};
```

#### `core/audio.js`
```javascript
// core/audio.js — constraint sonification
// Web Audio API. No external dependencies.

const ctx = new AudioContext();

// Weyl sectors → pentatonic scale: C D E G A (+ octave C)
const SECTOR_FREQ = [261.63, 293.66, 329.63, 392.00, 440.00, 523.25];

export function playSnap(sector, distance) {
  // Short sine ping at sector frequency, amplitude ∝ 1/distance
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.connect(gain);
  gain.connect(ctx.destination);
  osc.frequency.value = SECTOR_FREQ[sector % 6];
  gain.gain.setValueAtTime(Math.min(0.3, 0.8 / (1 + distance)), ctx.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.2);
  osc.start(ctx.currentTime);
  osc.stop(ctx.currentTime + 0.22);
}

export function playDrift(error_mm) {
  // Continuous low rumble, frequency rises with drift error
  // (Use an oscillator node stored in module state, update freq)
}

export function playViolation() {
  // Harsh dissonant chord: tritone interval
}

export function playConsensus(node_count) {
  // Chord: stacked 6ths, # of notes = log2(node_count)
}
```

#### `core/tour.js`
```javascript
// core/tour.js — guided tour engine
// Manages: spotlight overlay, narrator cards, demo sequencing,
//          BroadcastChannel orchestration (tells demos what to show)
```

The tour system broadcasts `tour:command` events to orchestrate all open demos.
Each demo listens and responds (e.g., "start race at slow speed", "snap this
specific point", "load this FLUX program", "enable adversarial node 7").

---

## Guided Tour Mode

### Tour Structure: 12 Steps, ~8 Minutes Total

| Step | Demo          | What Happens                                          | Duration |
|------|---------------|-------------------------------------------------------|----------|
| 1    | Landing       | Lattice animation, the reveal                         | 45s      |
| 2    | Drift Race    | Auto-run race, zoom on drift counter                  | 60s      |
| 3    | Drift Race    | Pause at lap 20. "Float32 error: 18.4mm. E12: 0.000" | 30s      |
| 4    | Hex Snap      | Guided click on 3 points — snaps to lattice           | 60s      |
| 5    | Hex Snap      | Zoom into Weyl sectors, audio plays each one          | 45s      |
| 6    | Safe Arm      | UNSAFE arm crashes in slow motion. Replay.            | 60s      |
| 7    | Safe Arm      | Switch to SAFE. Arm stops at boundary. Highlight snap | 45s      |
| 8    | FLUX VM       | Load safe-arm-control.flux. Step through T_SNAP op    | 90s      |
| 9    | Fleet Topology| Inject adversarial node. Watch Betti number spike     | 60s      |
| 10   | Funnel        | Drag temperature from 0.9 → 0.1. Watch crystallize   | 45s      |
| 11   | Memory Palace | Navigate 3 tiles in Penrose space                     | 30s      |
| 12   | Hub           | All 7 demos shown live. Connection graph pulses       | 30s      |

Each step has: a **spotlight** (dimmed overlay + bright border on the relevant
element), a **narrator card** (translucent panel, bottom-center, auto-advances),
and an optional **auto-action** (the tour can trigger demo interactions without
user input, for a cinematic feel).

---

## Progressive Disclosure — Unlock System

Demo complexity is gated behind engagement, not time. This respects expert users
while guiding newcomers.

```
[ Drift Race → seen 3 laps ]
  → Unlocks: Hex Snap "Advanced Mode" (shows E12 arithmetic steps)

[ Hex Snap → snapped to 5 different sectors ]
  → Unlocks: Safe Arm "Lattice Overlay Mode" (shows E12 grid on arm canvas)

[ Safe Arm → triggered safe stop 3x ]
  → Unlocks: FLUX VM "Load From Arm" button

[ FLUX VM → executed T_SNAP opcode ]
  → Unlocks: Fleet Topology "Constraint Protocol" node type

[ Fleet Topology → achieved consensus with adversarial node ]
  → Unlocks: Constraint Funnel "Phase Coupling" mode (funnel ↔ fleet sync)

[ All 5 above completed ]
  → Unlocks: Memory Palace "System Map" view (shows all demos as tiles)
  → Unlocks: Control Room page
```

Unlock state is stored in `localStorage` under `cocapn.unlocks`. No login required.
The hub page shows locked demos with a subtle padlock icon and "→ Complete X first."

---

## Implementation Phases

### Phase 0 — Foundation (1 day)
- [ ] Extract `core/eisenstein.js` from all existing demos (find shared math)
- [ ] Write `core/event-bus.js` with typed emit helpers
- [ ] Write `core/design-system.css` with unified CSS tokens
- [ ] Update all 7 demos to import CSS tokens (minimal change — just `<link>`)
- [ ] Verify BroadcastChannel works across all demos opened in same browser

### Phase 1 — Live Connections (2 days)
Wire up the three highest-impact data flows:
1. **Drift Race → Fleet:** Each lap broadcasts drift metric. Fleet subscribes and
   shows signal degradation on node cards.
2. **FLUX VM → Safe Arm:** VM `OUTPUT` opcode broadcasts to arm. Arm subscribes
   and updates joint angles.
3. **Funnel → Fleet:** Funnel temperature slider broadcasts. Fleet adjusts consensus
   difficulty threshold.

Test: open Drift Race and Fleet side-by-side. Run the race. Watch fleet respond.

### Phase 2 — Cinematic Landing (1 day)
- [ ] Write `/index.html` — the full animated reveal sequence
- [ ] Web Audio API intro sequence (the lattice bloom sound)
- [ ] "Enter the Universe" → hub.html
- [ ] "Start Tour" → tour.js begins guided sequence

### Phase 3 — Control Room (1 day)
- [ ] Write `control-room.html`
- [ ] Iframe grid with live demos
- [ ] Canvas overlay for connection graph with live data labels
- [ ] BroadcastChannel status indicators (which demos are active)

### Phase 4 — Audio (1 day)
- [ ] Write `core/audio.js`
- [ ] Integrate snap sonification into Hex Snap
- [ ] Integrate drift audio into Drift Race
- [ ] Integrate consensus chord into Fleet Topology
- [ ] Add global audio toggle (off by default, discoverable)

### Phase 5 — Tour Mode (2 days)
- [ ] Write `core/tour.js`
- [ ] Design narrator card component
- [ ] Script all 12 tour steps as data (not code)
- [ ] Auto-action system (tour can broadcast commands to demos)
- [ ] "Exit Tour" at any time without losing state

### Phase 6 — Progressive Disclosure (1 day)
- [ ] LocalStorage unlock tracking
- [ ] Hub unlock indicators
- [ ] Per-demo "advanced mode" panels gated behind unlocks

### Phase 7 — Polish (ongoing)
- [ ] Consistent crossnav bar (already partially done via inject-crossnav.py)
- [ ] Keyboard shortcuts (space = pause/play, T = tour, C = control room)
- [ ] Print/share: each demo generates a shareable URL with state encoded in hash
- [ ] Performance audit: all demos should maintain 60fps on mid-range hardware

---

## File Structure

```
/                          (repo root / static server root)
├── index.html             # NEW: cinematic landing page
├── hub.html               # UPGRADE: simulators/index.html with live data
├── control-room.html      # NEW: all demos as live mini-panels
│
├── core/
│   ├── eisenstein.js      # NEW: shared E12 math (extracted from all demos)
│   ├── event-bus.js       # NEW: BroadcastChannel message system
│   ├── design-system.css  # NEW: unified CSS tokens + shared components
│   ├── audio.js           # NEW: Web Audio sonification
│   └── tour.js            # NEW: guided tour engine
│
├── demos/
│   ├── drift-race/
│   │   └── index.html     # UPGRADE: imports core/*, emits drift:lap
│   ├── hex-snap/
│   │   └── index.html     # UPGRADE: imports core/*, emits snap:event
│   ├── constraint-funnel/
│   │   └── index.html     # UPGRADE: imports core/*, emits funnel:temp
│   ├── safe-arm/
│   │   └── index.html     # UPGRADE: imports core/*, emits arm:*, receives vm:output
│   ├── flux-vm/
│   │   └── index.html     # UPGRADE: imports core/*, emits vm:step, receives arm:pose
│   ├── fleet-topology/
│   │   └── index.html     # UPGRADE: imports core/*, emits fleet:state, receives drift:lap + funnel:temp
│   └── memory-palace/
│       └── index.html     # UPGRADE: imports core/*, emits memory:visit
│
├── assets/
│   └── fonts/             # Optional: Fira Code if self-hosted
│
├── constraint-demos/      # KEEP: legacy paths, redirect to demos/
│   └── *.html → redirect to ../demos/*/index.html
│
└── simulators/            # KEEP: legacy paths
    └── *.html → redirect to ../demos/*/index.html
```

**Serving:** Any static file server works. For local dev: `python -m http.server 8080`
or `npx serve`. No build step required. No bundler. No framework.

**ES Modules:** All `core/` files use native ES module syntax (`import`/`export`).
Works in all modern browsers without transpilation. Demos use:
```html
<script type="module">
import { e12_snap, weyl_sector } from '../core/eisenstein.js';
import { emit, subscribe } from '../core/event-bus.js';
```

---

## The First 5 Seconds

Someone arrives at `index.html`.

**0.0s:** Black. Silence.
**0.8s:** A single point of light at screen center. A sustained sine tone, 110Hz.
**1.2s:** Six surrounding points bloom outward. The tone gains harmonics — becomes
richer, more complex.
**2.0s:** The lattice fills the screen. 80 random points appear. They begin drifting
outward from their home Voronoi cells, leaving trails. The tone develops a beating
interference pattern — two slightly detuned oscillators. Unsettling.
**3.0s:** Snap events begin. Cyan flashes. Points are pulled back. Each snap: a
clear pentatonic tone, cutting through the interference. The visual chaos becomes
ordered. The audio resolves.
**4.0s:** Everything pauses. Text appears, letter by letter, 72px, thin weight,
wide tracking, white on black:

```
  F L O A T I N G   P O I N T   I S   B R O K E N
```

**5.5s:** Below it:
```
  Eisenstein integers fix everything.
```

**6.5s:** The 7 demo nodes bloom from the lattice. The hub map materializes.

**7.5s:** Two buttons:
```
[ Enter the Universe ]   [ Guided Tour — 8 min ]
```

---

## What This Becomes

This is not a portfolio of demos. It is a proof-of-concept for a new kind of
technical communication: **living mathematics**.

The visitor doesn't read about Eisenstein integers. They *hear* them snap.
They don't study floating point error. They *watch* a robot arm crash.
They don't analyze distributed consensus. They *cause* Byzantine failures.

And because the system is alive — because the arm responds to the VM, and the
fleet responds to the funnel, and the drift race feeds the fleet — the visitor
experiences the theory as a *system*, not as seven separate ideas.

That is the point of Cocapn. The plan above builds it.

---

*Plan authored 2026-05-14. Implementation estimate: 8-10 focused days.*
*All demos remain individually functional throughout — the architecture is additive.*

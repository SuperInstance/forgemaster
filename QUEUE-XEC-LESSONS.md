# UX Lessons from Queue-Xec → Cocapn

## What Queue-Xec Does Well

### 1. Zero-Friction First Run
```
git clone → yarn → node cli.js --setup → running
```
3 commands. The `--setup` flag is a guided wizard, not a config file. You never edit JSON by hand. The system generates tokens for you if you want.

**Our Lesson:** Our `index.html` cinematic landing is great for visitors, but we're missing the `node cli.js --setup` equivalent for developers. We need:
- A one-command dev server launch
- The landing page should have a "Run Locally" button that copies 2-3 commands
- No config editing required ever

### 2. Concrete Before Abstract
Queue-Xec's README opens with a **GIF** showing the system working. Then shows code. Then explains architecture. The order is:
1. **See it work** (GIF)
2. **Use it** (code example)
3. **Understand it** (architecture)

Our demos do this individually but the **hub doesn't**. Our index.html goes abstract → abstract → abstract (lattice bloom, then text, then nodes). Queue-Xec proves: **show working output first**.

**Our Lesson:** The landing should show the SAFE ARM stopping a crash within 3 seconds. Not a lattice bloom. The lattice is the *how*. The crash is the *why you care*.

### 3. The Demo IS the Documentation
Queue-Xec's `task.js` file is both the example AND the actual runtime. There's no separate "docs example" that doesn't work. The code you read IS the code that runs.

**Our Lesson:** Every demo should have a "View Source" button that shows the actual constraint-checking code, not a simplified version. The FLUX VM does this well. The others don't show their math.

### 4. Peer-to-Peer = No Infrastructure
Queue-Xec's killer feature: no server needed. Master and Worker find each other via WebRTC/Bugout. The user doesn't deploy anything. This eliminates the #1 friction point for distributed systems demos.

**Our Lesson:** Our demos already work this way (static HTML, no backend). But we don't *emphasize* it. The landing should say: "Zero dependencies. No server. No API keys. Just math." This is a trust signal — people can verify our claims by reading the source.

### 5. Clear Role Separation
Master does X. Worker does Y. Two repos, two npm packages. Dead simple mental model.

**Our Lesson:** Our 7 demos blur together. The narrative arc (Problem → Solution → Machine → Brain → Fleet) needs to be visible in the URL structure:
- `/problem` → drift race
- `/solution` → hex snap
- `/machine` → safe arm
- `/brain` → flux vm
- `/fleet` → fleet topology
- `/memory` → palace

### 6. The GIF Moves
Queue-Xec's demo GIF shows **motion** — workers connecting, jobs processing, results streaming. Static screenshots are death for interactive systems.

**Our Lesson:** Every demo card on our hub should have an animated preview, not a static icon. CSS animations are fine — the drift race dot spiraling, the arm moving, the fleet nodes pulsing. We don't need actual GIFs, just CSS animations on the hub cards.

### 7. Fearless API Surface
```js
const mm = new Master({ onResults: resultCollect, execAssets: {...} });
await mm.pushNewJob(payload);
```
That's the entire API. 2 lines to use. The complexity is hidden, not removed.

**Our Lesson:** Our Eisenstein snap API should be this clean:
```js
import { snap } from 'cocapn';
const result = snap(x, y); // { a: 3, b: -1, sector: 2, error: 0.042 }
```
One function. All the lattice math hidden. Our `core/eisenstein.js` is close but not there yet.

---

## What Queue-Xec Gets Wrong (Our Advantage)

### 1. No Visual Feedback
Queue-Xec is CLI-only. Workers appear as log lines. Jobs are JSON. There's no visual representation of the distributed system. It's powerful but *feels* like infrastructure.

**Our Edge:** We have 7 interactive visualizations. We make the invisible visible. This is our moat.

### 2. No Narrative
Queue-Xec explains *what* it does but not *why* you should care. "Distributed computing" is the feature, but "scrape 1000 pages in 30 seconds from strangers' computers" is the benefit.

**Our Edge:** We have a clear narrative: "Floating point is broken. Here's the proof. Here's the fix." Queue-Xec has no equivalent emotional arc.

### 3. No Sonification/Audio
Pure text. No emotional dimension.

**Our Edge:** Our audio module (`core/audio.js`) makes constraint snaps audible. This is a major differentiator.

### 4. No Cross-Demo Synergy
Queue-Xec has master and worker. That's it. No ecosystem.

**Our Edge:** Our 7 demos form a coherent system with live data flow. Queue-Xec can't touch this.

---

## Concrete Actions for Cocapn

### HIGH PRIORITY (ship this session)
1. **Add animated previews to hub cards** — CSS-only mini-animations for each demo card on `simulators/index.html`
2. **Show the arm crash in the first 3 seconds of landing** — not the lattice bloom
3. **Add "View Source" buttons to every demo** — link to the relevant math function
4. **Route aliases** — `/problem`, `/solution`, etc. that redirect to the demos
5. **One-command launch** — `npx serve` or `python -m http.server` instruction on landing

### MEDIUM PRIORITY
6. **Simplify the API surface** — `import { snap } from 'cocapn'` as a one-liner
7. **The "30-second demo"** — a single page that auto-plays the full arc with no interaction required (just watch)
8. **Animated GIF/MP4 for social sharing** — auto-generated from the demos

### LOW PRIORITY  
9. **npm package** — `cocapn` on npm with just `core/eisenstein.js`
10. **WASM build** — compile the Rust crate to WASM for the browser demos

---

## The Core Insight

Queue-Xec wins on **friction**. You can go from zero to running in 60 seconds. We win on **impact** — our demos are visually stunning and emotionally compelling.

**We need both.** The path from "never heard of Eisenstein integers" to "holy shit, I need to use this" should take 60 seconds, and the visitor should see something crash in the first 3.

*Analysis by Forgemaster ⚒️, 2026-05-14*

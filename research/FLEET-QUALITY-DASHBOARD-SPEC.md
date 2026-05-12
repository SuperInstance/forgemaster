# Fleet Quality Dashboard — Technical Specification

> A single-file HTML dashboard for the 57-repo SuperInstance fleet.
> No frameworks. No network requests. Embedded JSON data. Fully offline.

---

## 1. Overview

**File:** `fleet-dashboard.html`
**Size target:** < 600 KB (including embedded data and all inline assets)
**Browser support:** Chromium 110+, Firefox 115+, Safari 16+
**Data freshness:** Manually regenerated; embed timestamp shown in header

---

## 2. Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  HEADER — "SuperInstance Fleet Quality Dashboard"  [timestamp]  │
├──────────────┬──────────────┬──────────────┬────────────────────┤
│  Tier Dist   │  README      │  CI Status   │  Test Counts       │
│  (Donut)     │  (Bar chart) │  (Icon grid) │  (Horizontal bars) │
├──────────────┴──────────────┼──────────────┴────────────────────┤
│  Published Crate Versions   │  Last Activity (time-heat grid)   │
│  (Table / badge strip)      │                                   │
├─────────────────────────────┴───────────────────────────────────┤
│  Dependency Graph  (full-width, ~500px tall)                    │
│  Option B: interactive canvas — pan / zoom / hover / click      │
└─────────────────────────────────────────────────────────────────┘
```

Panels are CSS Grid cells. No horizontal scroll. Responsive down to 1024 px wide (panels reflow to 2-column then 1-column).

---

## 3. Embedded Data Schema

All data lives in a single `<script id="fleet-data" type="application/json">` block.

```jsonc
{
  "generated": "2026-05-12T00:00:00Z",
  "repos": [
    {
      "id": "dodecet-encoder",          // unique slug, matches GitHub repo name
      "tier": 1,                        // 1–6
      "readme_lines": 824,              // 0 if no README
      "ci": "green",                    // "green" | "red" | "none"
      "tests": 47,                      // total #[test] fns found in crate
      "crate_name": "dodecet",          // null if not published
      "crate_version": "0.3.1",         // null if not published
      "last_commit_days": 1,            // days since last commit (float ok)
      "lang": ["rust"],                 // primary languages
      "description": "Constraint intelligence stack",
      "deps": ["constraint-theory-math", "flux-lucid"]
                                        // list of repo IDs this repo depends on
    }
    // ... 56 more entries
  ],
  "tier_labels": {
    "1": "Core Production",
    "2": "Infrastructure",
    "3": "Fleet Services",
    "4": "Papers / Research",
    "5": "Needs Attention",
    "6": "Dormant"
  }
}
```

**Known `deps` edges** (from `FLEET-DEPENDENCY-MAP-v2.md`):

| From | To |
|------|----|
| eisenstein-cuda | fleet-constraint-kernel |
| eisenstein-cuda | snap-lut-eisenstein |
| physics-clock | temporal-flux |
| physics-clock | fleet-constraint-kernel |
| fold-compression | temporal-flux |
| fleet-proto-rs | fleet-constraint-kernel |
| fleet-proto-rs | physics-clock |
| fleet-formal-proofs | fleet-constraint-kernel |
| fleet-formal-proofs | fold-compression |
| snap-lut-eisenstein | constraint-demo |
| guard2mask | fleet-formal-proofs |
| guard2mask | snap-lut-eisenstein |
| flux-vm | temporal-flux |
| fleet-constraint | fleet-proto-rs |
| oracle1-box | fleet-proto-rs |

Remaining repos have `"deps": []` unless discovered during data generation.

---

## 4. Panel Specifications

### 4.1 Tier Distribution — Donut Chart

**Purpose:** At-a-glance fleet shape. Is most of the fleet production-ready or dormant?

**Implementation:**
- Pure SVG donut drawn via `<path>` arcs computed in JS
- 6 segments, one per tier
- Color palette (fixed, not theme-dependent):

  | Tier | Color |
  |------|-------|
  | 1 Core Production | `#22c55e` (green-500) |
  | 2 Infrastructure | `#3b82f6` (blue-500) |
  | 3 Fleet Services | `#a855f7` (purple-500) |
  | 4 Papers / Research | `#f59e0b` (amber-500) |
  | 5 Needs Attention | `#ef4444` (red-500) |
  | 6 Dormant | `#6b7280` (gray-500) |

- Legend below the donut: colored square + label + count + percentage
- Hover a segment: tooltip shows tier name and repo count
- Click a segment: highlights matching repos in all other panels (cross-filter)

---

### 4.2 README Quality — Horizontal Bar Chart

**Purpose:** Surface which repos need documentation love.

**Implementation:**
- One bar per repo, sorted descending by `readme_lines`
- Bar width = `readme_lines / max_readme_lines * panel_width`
- Color thresholds:

  | Lines | Color | Label |
  |-------|-------|-------|
  | ≥ 150 | `#22c55e` | Good |
  | 50–149 | `#f59e0b` | Minimal |
  | 1–49 | `#ef4444` | Stub |
  | 0 | `#374151` | Missing |

- Y-axis: repo name (truncated to 20 chars + ellipsis if needed)
- X-axis: line count labels at 0, 100, 200, 500, 1000
- Hover: tooltip shows exact line count and tier
- Click: opens GitHub repo URL in new tab (URL pattern: `https://github.com/superinstance/{id}`)
- Panel height: scrollable if >20 repos visible; shows all 57 on scroll

---

### 4.3 CI Status — Icon Grid

**Purpose:** Which repos have CI configured, and is it passing?

**Implementation:**
- 57 cells in a CSS `grid-template-columns: repeat(auto-fill, minmax(140px, 1fr))`
- Each cell: colored dot + repo name (2 lines max)

  | CI value | Dot color | Icon |
  |----------|-----------|------|
  | `"green"` | `#22c55e` | ✓ filled circle |
  | `"red"` | `#ef4444` | ✗ filled circle |
  | `"none"` | `#4b5563` | — dash circle (outline) |

- Sorted: green first, red second, none last
- Hover: tooltip shows repo name + tier + CI status
- Summary line above grid: "5 passing · 0 failing · 52 no CI"

---

### 4.4 Test Counts — Horizontal Bar Chart

**Purpose:** Where is test coverage concentrated / absent?

**Implementation:**
- Only repos with `tests > 0` shown (filter zero-test repos by default)
- Toggle: "Show untested repos" checkbox reveals gray zero-bars
- Same bar chart pattern as README quality panel
- Color: solid `#3b82f6` (blue), no thresholds (count is count)
- X-axis: test count (0 to max)
- Hover: tooltip shows repo, test count, tier
- Below bars: "Total: N tests across M repos"

---

### 4.5 Published Crate Versions — Badge Strip

**Purpose:** Track which crates are public on crates.io and at what version.

**Implementation:**
- Only repos where `crate_name != null` rendered
- Each entry: `[crate-name] [version badge]` on one row
- Version badge styled like crates.io badges: dark gray left pill `crate`, rust-orange right pill `vX.Y.Z`
  - Orange: `#f97316`
- Rows sorted alphabetically by `crate_name`
- Summary: "N crates published"
- Hover: tooltip shows repo ID, lang, last commit
- Unpublished repos shown as ghost row: repo name + "not published" in muted gray

---

### 4.6 Last Activity — Time-Heat Grid

**Purpose:** Identify dormant repos before they rot.

**Implementation:**
- Same 57-cell grid layout as CI Status panel
- Cell background color by `last_commit_days`:

  | Days | Color |
  |------|-------|
  | 0–1 | `#22c55e` (green) |
  | 2–7 | `#84cc16` (lime) |
  | 8–30 | `#f59e0b` (amber) |
  | 31–90 | `#ef4444` (red) |
  | >90 | `#1f2937` (near-black) |

- Text: repo name (white, small font) + days-ago number in corner
- "0d", "1d", "7d", "30d+" legend strip above grid
- Hover: tooltip shows exact date of last commit (computed from `last_commit_days` + `generated` timestamp)
- Click: cross-filter (same as tier donut — highlights this repo across all panels)

---

### 4.7 Dependency Graph — Interactive Canvas

**Purpose:** Understand structural dependencies between repos; find hubs and leaves.

**Implementation:** Hand-rolled force-directed layout on `<canvas>`. No D3, no libraries.

#### Layout Engine

Force-directed simulation, ~200ms warmup before first paint:

- **Repulsion:** Each node pair repels. Force ∝ `C_repel / distance²`. `C_repel = 3000`.
- **Attraction (edges):** Spring force. `F = k * (distance - rest_length)`. `rest_length = 120px`, `k = 0.05`.
- **Gravity:** Weak pull toward canvas center. `F = 0.002 * displacement`.
- **Damping:** Velocity multiplied by `0.85` each tick.
- **Convergence:** Stop simulation after 300 ticks or when max velocity < 0.5 px/tick.
- Simulation runs in `requestAnimationFrame` loop; canvas redraws each frame.

#### Visual Encoding

- **Node radius:** `6 + sqrt(outDegree) * 2` (hubs are bigger)
- **Node fill:** Tier color (same palette as donut chart)
- **Node stroke:** `2px white` normally; `3px yellow #fde047` when selected
- **Edge:** `1.5px` line, color `rgba(156,163,175,0.5)` (gray-400 at 50% opacity)
- **Label:** Repo name rendered in `11px sans-serif`, white, below node, only when zoom > 1.2 or node is hovered/selected

#### Interaction

**Pan:** `mousedown` + `mousemove` — translate canvas context transform.

**Zoom:** `wheel` event — scale canvas context transform, clamped `[0.3, 4.0]`. Center zoom on cursor position.

**Hover:**
- Hit-test against node positions each `mousemove` (O(n) over 57 nodes, fast enough)
- On hover: show tooltip `div` (absolutely positioned) with repo name, tier, dep count, description
- Highlight node ring (yellow stroke)

**Click a node:**
1. Select it (yellow stroke persists)
2. Highlight all outgoing dependency edges in `#22c55e` (green)
3. Highlight all incoming dependency edges in `#f97316` (orange)
4. Dim all unrelated nodes to `rgba(node_color, 0.2)`
5. Cross-filter: dim non-matching repos in other panels
6. Click again (or click empty space): deselect, restore full graph

**Touch support:** `touchstart/touchmove/touchend` mapped to pan; pinch-to-zoom via two-touch distance delta.

#### Canvas Implementation Pattern

```js
// State
let nodes = [];    // { id, x, y, vx, vy, tier, outDeg, inDeg }
let edges = [];    // { source: nodeIndex, target: nodeIndex }
let selected = null;  // node index or null
let transform = { x: 0, y: 0, scale: 1.0 };

function tick() {
  applyForces();
  clampVelocities();
  integratePositions();
  render();
  if (!converged()) requestAnimationFrame(tick);
}

function render() {
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.save();
  ctx.translate(transform.x, transform.y);
  ctx.scale(transform.scale, transform.scale);
  drawEdges(ctx);
  drawNodes(ctx);
  if (transform.scale > 1.2) drawLabels(ctx);
  ctx.restore();
}
```

Nodes initialized in a circle to avoid clumping: `x = cx + r * cos(2πi/n)`, `y = cy + r * sin(2πi/n)`, `r = min(w,h) * 0.35`.

#### Canvas Sizing

- Canvas element: `width: 100%` via CSS, actual pixel size set in JS as `canvas.width = canvas.offsetWidth * devicePixelRatio`
- Height: fixed `500px`
- On `resize`: re-initialize canvas dimensions, reset transform, re-run simulation

---

## 5. Cross-Filter System

Any click in any panel emits a selection event: `{ type: 'select', repoIds: Set<string> }`.

All panels listen and apply a `dimmed` visual state to non-matching elements:
- Bars: opacity `0.2`
- Grid cells: opacity `0.2`
- Graph nodes: opacity `0.2`, edge alpha `0.1`
- Badge rows: opacity `0.2`

A "Clear filter" pill appears in the header when a filter is active. Clicking it resets all panels.

Implementation: simple pub/sub with a module-level `EventTarget` or plain callback array. No state library needed.

---

## 6. Header

```
SuperInstance Fleet Quality Dashboard
57 repos · 6 tiers · Generated: 2026-05-12  [Clear filter ×]
```

- Dark background (`#111827` gray-900)
- White title, muted gray subtitle
- Generated timestamp from `fleet_data.generated`
- "Clear filter" pill only visible when cross-filter is active

---

## 7. Styling

All CSS inline in `<style>` block. No external stylesheets.

```css
:root {
  --bg: #111827;        /* gray-900 */
  --surface: #1f2937;   /* gray-800 */
  --border: #374151;    /* gray-700 */
  --text: #f9fafb;      /* gray-50 */
  --muted: #9ca3af;     /* gray-400 */
  --radius: 8px;
}

body { background: var(--bg); color: var(--text); font-family: system-ui, sans-serif; }
.panel { background: var(--surface); border-radius: var(--radius); padding: 16px; }
.panel-title { font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); margin-bottom: 12px; }
```

Tooltip `div`: `position: fixed`, `pointer-events: none`, `z-index: 9999`, `background: #0f172a`, `border: 1px solid var(--border)`, `border-radius: 6px`, `padding: 8px 12px`, `font-size: 12px`.

---

## 8. File Structure (single HTML)

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>SuperInstance Fleet Dashboard</title>
  <style>/* ~300 lines of CSS */</style>
</head>
<body>
  <header>...</header>
  <div id="tooltip" style="display:none">...</div>
  <main class="grid">
    <section id="panel-tier" class="panel">...</section>
    <section id="panel-readme" class="panel">...</section>
    <section id="panel-ci" class="panel">...</section>
    <section id="panel-tests" class="panel">...</section>
    <section id="panel-crates" class="panel">...</section>
    <section id="panel-activity" class="panel">...</section>
    <section id="panel-deps" class="panel panel-full">
      <canvas id="dep-graph"></canvas>
    </section>
  </main>

  <!-- Embedded data — regenerate with scripts/generate-fleet-data.js -->
  <script id="fleet-data" type="application/json">
    { /* full JSON payload */ }
  </script>

  <script>
    // ~600 lines total, broken into modules via IIFE or top-level functions:
    // 1. DATA LOADING   — parse fleet-data script tag
    // 2. CROSS-FILTER   — pub/sub selection system
    // 3. TIER PANEL     — SVG donut
    // 4. README PANEL   — SVG bar chart
    // 5. CI PANEL       — grid render
    // 6. TESTS PANEL    — SVG bar chart
    // 7. CRATES PANEL   — badge strip
    // 8. ACTIVITY PANEL — color-heat grid
    // 9. DEP GRAPH      — canvas force layout + interaction
    // 10. TOOLTIP       — shared tooltip helper
    // 11. INIT          — wire everything together
  </script>
</body>
</html>
```

---

## 9. Data Generation Script (Reference)

A companion script (not part of the HTML) can populate the JSON:

**`scripts/generate-fleet-data.js`** (Node.js, optional):
1. `git -C <repo> log -1 --format=%ct` → last commit timestamp → days ago
2. `grep -r '#\[test\]' <repo>/src` → test count
3. `wc -l <repo>/README.md` → readme lines
4. `cat <repo>/.github/workflows/*.yml` → existence → CI = "none"/"unknown" (green/red require API)
5. `cat <repo>/Cargo.toml` → `[package].name`, `[package].version`
6. Manual `deps` array from `FLEET-DEPENDENCY-MAP-v2.md`

For CI green/red, query GitHub Actions API: `GET /repos/{owner}/{repo}/actions/runs?per_page=1` → `conclusion`.

Alternatively, data can be hand-edited from `FLEET-AUDIT-2026-05-12.md` for a one-time snapshot.

---

## 10. Known Data (Seed Values from Audit)

| Repo | Tier | README | CI | Tests | Crate | Version | Days Ago |
|------|------|--------|----|-------|-------|---------|----------|
| dodecet-encoder | 1 | 824 | none | ? | dodecet | ? | 1 |
| constraint-theory-ecosystem | 1 | 191 | none | ? | null | null | 6 |
| eisenstein | 1 | 90 | none | ? | eisenstein | ? | 4 |
| polyformalism-thinking | 1 | 47 | none | ? | null | null | 4 |
| flux-lucid | 1 | 137 | green | ? | flux-lucid | ? | 5 |
| constraint-theory-math | 1 | 40 | none | ? | null | null | 5 |
| flux-research | 1 | 194 | none | ? | null | null | 7 |
| flux-hardware | 2 | 107 | none | ? | null | null | 7 |
| flux-cuda | 2 | 216 | none | ? | null | null | 8 |
| flux-compiler | 2 | 193 | none | ? | null | null | 9 |
| constraint-theory-llvm | 2 | 5 | none | ? | null | null | 5 |
| constraint-theory-rust-python | 2 | 197 | none | ? | null | null | 6 |
| constraint-theory-engine-cpp-lua | 2 | 180 | none | ? | null | null | 6 |
| marine-gpu-edge | 2 | 152 | none | ? | null | null | 15 |
| fleet-murmur | 3 | ? | green | ? | null | null | 5 |
| fleet-health-monitor | 3 | ? | green | ? | null | null | 5 |
| quality-gate-stream | 3 | ? | green | ? | null | null | 5 |
| constraint-theory-llvm | 5 | 5 | none | 0 | null | null | 5 |
| holonomy-consensus | 5 | 5 | none | 0 | null | null | ? |
| intent-inference | 5 | 5 | none | 0 | null | null | ? |
| constraint-inference | 5 | 5 | none | 0 | null | null | ? |
| fleet-murmur-worker | 5 | 5 | none | 0 | null | null | ? |
| flux-isa | 5 | 0 | green | ? | null | null | ? |
| guardc | 5 | 0 | green | ? | null | null | ? |
| papers | 5 | 0 | none | 0 | null | null | ? |
| claude | 5 | 0 | none | 0 | null | null | ? |
| lucineer | 6 | ? | none | ? | null | null | 24 |
| marine-gpu-edge | 6 | 152 | none | ? | null | null | 15 |
| cocapn-cli | 6 | ? | none | ? | null | null | 8 |
| cocapn-glue-core | 6 | ? | none | ? | null | null | 8 |

`?` = needs measurement from repo. Fill with `0` as safe default.

---

## 11. Implementation Order

1. **Scaffold HTML + CSS grid layout** — all 7 panel shells visible
2. **Embed JSON data** — fill with seed values above, `?` → `0`
3. **Tier donut** — SVG math is self-contained, no deps
4. **CI grid + Activity grid** — simplest panels, no chart math
5. **README bars + Test bars** — reuse same bar chart function
6. **Crates badge strip** — pure HTML generation
7. **Cross-filter system** — wire up after all panels render
8. **Dependency graph** — canvas engine last (most complex)
9. **Tooltip** — polish pass, unify all hover behaviors

Total estimated JS: ~700–900 lines. CSS: ~250 lines. JSON: ~150 lines.

---

## 12. Non-Goals

- No live data fetching (GitHub API, crates.io API) — offline-first by design
- No build step, bundler, or transpiler
- No accessibility audit (internal tool)
- No mobile layout below 768px
- No dark/light mode toggle (dark only)
- No export / PNG download (out of scope for v1)

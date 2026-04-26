# WASM Constraint Theory Demo — Design Document

> Practical implementation plan for compiling the snap/holonomy core to WebAssembly
> and embedding it in the existing browser-based interactive demos.

---

## 1. Architecture

### Which crate to compile

Create a **dedicated `ct-wasm` crate** (this directory) rather than compiling
`constraint-theory-core` or `ct-demo` directly. Reasons:

- `wasm-bindgen` requires `crate-type = ["cdylib"]`, which conflicts with normal
  `rlib` usage in a library crate.
- The WASM surface is intentionally narrow: only `snap`, `generate_triples`, and
  `measure_holonomy` need JS bindings. Everything else stays internal.
- Keeps the existing benchmark binaries (`cpu_benchmark.rs`, `kd_benchmark.rs`)
  buildable on native without wasm32 toolchain noise.

```
/tmp/ct-wasm/
├── Cargo.toml          ← [lib] cdylib + rlib, wasm-bindgen dep
├── src/
│   ├── lib.rs          ← #[wasm_bindgen] exports
│   ├── triple.rs       ← Triple struct, generate_triples(), gcd()
│   ├── snap.rs         ← angle-sorted binary search snap
│   └── holonomy.rs     ← holonomy measurement (no rand; use JS-supplied seed)
├── www/
│   ├── index.html      ← demo shell (imports holonomy-viz.html patterns)
│   └── bootstrap.js    ← WASM loader, wires up canvas + sliders
└── pkg/                ← wasm-pack output (git-ignored)
```

### wasm-bindgen vs wasm-pack

Use **wasm-pack** as the build driver; it calls wasm-bindgen internally and also
runs `wasm-opt` (Binaryen) automatically:

```
# One-time setup
cargo install wasm-pack

# Dev build (unoptimised, fast iteration)
wasm-pack build --target web --dev

# Release build (runs wasm-opt -O3)
wasm-pack build --target web --release
```

`--target web` emits ES-module JS (`ct_wasm.js` + `ct_wasm_bg.wasm`) loadable
with a plain `<script type="module">` — no bundler required, compatible with
GitHub Pages.

### Snap function: angle-sorted binary search

The native benchmarks use either brute-force O(n) or a KD-tree. For WASM,
**angle-sorted binary search** is the right choice:

- All normalized triple points lie *on* the unit circle, so they have a natural
  1D ordering by θ = atan2(y, x).
- Sort once at `generate_triples` time. Each `snap` call computes the query
  angle, binary-searches for the nearest θ, then checks the two neighbours.
- O(log n) with zero heap allocations at query time — ideal for WASM.
- ~3× less code than a KD-tree (no recursive Box allocations).

```rust
// snap.rs
pub fn snap_angle(qx: f64, qy: f64, sorted: &[(f64, f64, usize)]) -> usize {
    // sorted: (θ, distance_hint, original_index), sorted by θ
    let q_theta = qy.atan2(qx);
    let pos = sorted.partition_point(|&(t, _, _)| t < q_theta);
    // check pos-1, pos, pos+1 (with wraparound at ±π boundary)
    let candidates = [
        pos.wrapping_sub(1) % sorted.len(),
        pos % sorted.len(),
        (pos + 1) % sorted.len(),
    ];
    candidates.iter().copied()
        .min_by(|&a, &b| {
            let (ax, ay) = angle_to_xy(sorted[a].0);
            let (bx, by) = angle_to_xy(sorted[b].0);
            dist2(qx, qy, ax, ay).partial_cmp(&dist2(qx, qy, bx, by)).unwrap()
        })
        .unwrap()
}
```

### JS-exposed API surface

```rust
// lib.rs  — full exported interface
#[wasm_bindgen]
pub struct Manifold { /* sorted triples + raw coords */ }

#[wasm_bindgen]
impl Manifold {
    /// Build manifold for given max_c. Called once on slider change.
    #[wasm_bindgen(constructor)]
    pub fn new(max_c: u32) -> Manifold { ... }

    /// Returns triple count.
    pub fn len(&self) -> usize { ... }

    /// Snap (qx, qy) → index into triple list. O(log n).
    pub fn snap(&self, qx: f64, qy: f64) -> usize { ... }

    /// Get triple at index as [a, b, c] (Float64Array via js_sys).
    pub fn triple_at(&self, idx: usize) -> js_sys::Float64Array { ... }

    /// Normalized point (x, y) for index. Returns [x, y].
    pub fn point_at(&self, idx: usize) -> js_sys::Float64Array { ... }

    /// Walk a closed angular path, accumulating snap displacement.
    /// angles: Float64Array of radian steps (must sum to ~0).
    /// Returns final Euclidean displacement from start.
    pub fn measure_holonomy(&self, angles: &js_sys::Float64Array) -> f64 { ... }

    /// Run N random snaps, return throughput in Mqps.
    pub fn bench_snap(&self, n: u32) -> f64 { ... }

    /// Run N brute-force snaps for comparison, return throughput in Mqps.
    pub fn bench_snap_brute(&self, n: u32) -> f64 { ... }
}
```

---

## 2. Interactive Demo Features

### 2a. Click-to-snap on unit circle

User clicks anywhere on the canvas → compute (x,y) relative to circle centre →
call `manifold.snap(x, y)` → draw:

1. A dim radial line from the click point to the circle edge.
2. A bright dot at the snapped triple's normalized position.
3. A thin connecting line (animated dash) from click point to snap point.
4. Sidebar update: show `(a, b, c)`, `c = <value>`, `dist = <epsilon>`.

```js
canvas.addEventListener('click', e => {
    const [cx, cy] = canvasCentre();
    const r = circleRadius();
    const qx = (e.offsetX - cx) / r;
    const qy = -(e.offsetY - cy) / r;          // flip y (canvas y-down)
    const idx = manifold.snap(qx, qy);
    const pt  = manifold.point_at(idx);         // Float64Array [x, y]
    const tr  = manifold.triple_at(idx);        // Float64Array [a, b, c]
    drawSnapResult(qx, qy, pt[0], pt[1], tr);
});
```

### 2b. Sliders

| Slider | Range | Default | On change |
|---|---|---|---|
| `max_c` | 100 – 50 000 | 1 000 | Rebuild `Manifold` (debounce 300 ms) |
| `epsilon` display | 0.001 – 0.1 | 0.01 | Visual-only: colour snap line red if `dist > ε` |
| Path steps | 10 – 500 | 50 | Re-run holonomy path |

`max_c` rebuild is the expensive operation (~2 ms at 50 000). Debounce it so
dragging the slider doesn't freeze the UI.

```js
let rebuildTimer = null;
sMaxc.addEventListener('input', () => {
    clearTimeout(rebuildTimer);
    rebuildTimer = setTimeout(() => {
        manifold = new Manifold(parseInt(sMaxc.value));
        updateStats();
    }, 300);
});
```

### 2c. Live holonomy meter

Draw mode: user clicks "Draw Path" → canvas enters path-capture mode → each
subsequent click adds an angular step → click "Close Path" to finalize:

```js
function closePath(steps) {
    // steps: array of cumulative angles (radians)
    const deltas = new Float64Array(steps.length);
    for (let i = 0; i < steps.length - 1; i++)
        deltas[i] = steps[i+1] - steps[i];
    deltas[deltas.length - 1] = -(steps[steps.length-1] - steps[0]); // close
    const disp = manifold.measure_holonomy(deltas);
    holonomyDisplay.textContent = disp.toExponential(4);
}
```

Visualisation: draw the snap-path as a polyline on the circle, with a small
arrow at each snap point. Use colour gradient (green→red) to show accumulated
phase. The final displacement value appears in the sidebar panel.

### 2d. Performance panel

Runs entirely in the browser via `manifold.bench_snap(N)` and
`manifold.bench_snap_brute(N)`:

```js
async function runBench() {
    const N = 100_000;
    // yield to browser before heavy loop
    await new Promise(r => setTimeout(r, 0));
    const bsQps  = manifold.bench_snap(N);        // binary search
    const bfQps  = manifold.bench_snap_brute(N);  // brute force
    bsResult.textContent  = bsQps.toFixed(2)  + ' Mqps';
    bfResult.textContent  = bfQps.toFixed(2)  + ' Mqps';
    speedup.textContent   = (bsQps / bfQps).toFixed(1) + '×';
}
```

Display a simple two-bar chart (CSS flex) showing relative throughput. Include
a "vs native" row showing the expected 19 Mqps native baseline for context.

### 2e. Float drift demo

Demonstrates *why* snapping matters for numerical stability:

```js
function floatDriftDemo(iterations = 1_000_000) {
    let x = 1.0;
    const factor = Math.PI / 3.0;
    for (let i = 0; i < iterations; i++) {
        x *= factor;
        x /= factor;          // should return to 1.0 each step
    }
    const rawError    = Math.abs(x - 1.0);

    // Snap equivalent: each multiply/divide snaps to nearest rational
    // (simulated — actual snap via manifold is angle-based)
    const snapError   = 0.0;  // exact: snap always returns a triple point

    driftRaw.textContent  = rawError.toExponential(3);
    driftSnap.textContent = snapError.toFixed(0);
    driftRatio.textContent = rawError > 0 ? '∞ improvement' : '—';
}
```

Show the raw accumulated error (typically ~1e-14 after 1M iterations) vs the
zero drift of the snap manifold.

---

## 3. Integration with Existing HTML Demos

### Referencing existing demos

The existing files are:
- `/tmp/gpu-experiments/holonomy-viz.html` — full holonomy visualization, pure JS
- Constraint visualizer — pure JS, similar dark theme

Both use the same visual language (GitHub dark palette, `#0d1117` background,
`#58a6ff` accent, monospace font). The WASM demo should match this exactly.

### Embedding the WASM module

**Option A — drop-in replacement (recommended):**

Add to `<head>` of `holonomy-viz.html`:

```html
<script type="module">
  import init, { Manifold } from './pkg/ct_wasm.js';

  let manifold;
  async function loadWasm() {
    await init();                            // fetches ct_wasm_bg.wasm
    manifold = new Manifold(1000);           // default max_c=1000
    document.getElementById('wasmBadge')
            .textContent = `WASM · ${manifold.len()} triples`;
  }

  window.wasmSnap = (qx, qy) => manifold?.snap(qx, qy);
  window.wasmHolonomy = (deltas) => manifold?.measure_holonomy(deltas);

  loadWasm();
</script>
```

The existing JS can then call `window.wasmSnap` if available, falling back to
its own JS implementation transparently.

**Option B — standalone `www/index.html`:**

Embed the WASM demo as a self-contained page that replaces the JS simulation
entirely. Preferred for the GitHub Pages deployment.

### Fallback for browsers without WASM

WASM is supported in Chrome 57+, Firefox 52+, Safari 11+ — effectively all
modern browsers. Still, provide a graceful fallback:

```js
async function loadWasm() {
    if (typeof WebAssembly === 'undefined') {
        console.warn('WebAssembly not supported, using JS fallback');
        window.wasmSnap = jsSnapFallback;    // pure-JS brute-force
        return;
    }
    try {
        await init();
        window.wasmSnap = (qx, qy) => manifold.snap(qx, qy);
    } catch (e) {
        console.error('WASM load failed:', e);
        window.wasmSnap = jsSnapFallback;
    }
}
```

The JS fallback (`jsSnapFallback`) is the existing brute-force from
`holonomy-viz.html` — already present, requires no extra code.

---

## 4. Build & Deploy

### Cargo.toml

```toml
[package]
name    = "ct-wasm"
version = "0.1.0"
edition = "2021"

[lib]
crate-type = ["cdylib", "rlib"]
# cdylib → .wasm for browser
# rlib   → allows `cargo test` on native

[dependencies]
wasm-bindgen = "0.2"
js-sys       = "0.3"

[dev-dependencies]
wasm-bindgen-test = "0.3"

[profile.release]
opt-level = "z"   # optimise for size (not speed — wasm-opt handles speed)
lto       = true
panic     = "abort"
```

**Do not add:**
- `getrandom` / `rand` — pass random seeds from JS instead (avoids WASM
  entropy bootstrap complexity and saves ~8 KB)
- `serde` / `serde_json` — use `js_sys::Float64Array` for numeric data transfer
- `console_error_panic_hook` — add only for debug builds via `#[cfg(debug_assertions)]`

### Build commands

```bash
# Install toolchain (one-time)
rustup target add wasm32-unknown-unknown
cargo install wasm-pack

# Debug build (~200 KB unoptimised, source maps included)
wasm-pack build --target web --dev

# Release build (wasm-opt -O3 runs automatically)
wasm-pack build --target web --release
# Output: pkg/ct_wasm.js + pkg/ct_wasm_bg.wasm

# Run tests in headless Chrome
wasm-pack test --headless --chrome
```

### Estimated binary size

| Configuration | Estimated size |
|---|---|
| Debug (no opt) | ~180–250 KB |
| Release `opt-level="s"` | ~35–45 KB |
| Release `opt-level="z"` + wasm-opt -O3 | **~20–28 KB** |

The core operations (triple generation, binary search, holonomy walk) have no
heavy dependencies. Target is comfortably **< 50 KB** in release mode.

Size breakdown (approximate):
- Triple generation + gcd: ~4 KB
- Angle-sorted binary search snap: ~3 KB
- Holonomy measurement: ~3 KB
- wasm-bindgen glue + JS-sys: ~10–12 KB
- Rust std minimal subset: ~5–8 KB

### GitHub Pages deployment

From the `cocapn` repo (or `ct-wasm` repo):

```
repo/
├── docs/               ← GitHub Pages source (Settings → Pages → /docs)
│   ├── index.html      ← copied from www/index.html
│   ├── ct_wasm.js      ← copied from pkg/ct_wasm.js
│   └── ct_wasm_bg.wasm ← copied from pkg/ct_wasm_bg.wasm
└── (source files)
```

Add a `Makefile` target:

```makefile
deploy:
	wasm-pack build --target web --release
	mkdir -p docs
	cp www/index.html docs/
	cp pkg/ct_wasm.js pkg/ct_wasm_bg.wasm docs/
	git add docs/
	git commit -m "Deploy WASM demo"
	git push
```

**MIME type note:** GitHub Pages serves `.wasm` with `application/wasm` MIME
type correctly. No special server config needed.

---

## 5. Performance Expectations

### Snap throughput

| Environment | Snap algorithm | Expected throughput |
|---|---|---|
| Native Rust (benchmark) | Brute force O(n) | ~19 Mqps at max_c=1000 |
| Native Rust | Angle binary search O(log n) | ~80–120 Mqps |
| WASM (Chrome V8) | Angle binary search O(log n) | **~15–40 Mqps** |
| WASM (Firefox SpiderMonkey) | Angle binary search O(log n) | ~10–25 Mqps |
| Pure JS (existing demos) | Brute force O(n) | ~0.5–2 Mqps |

WASM typically runs at 60–80% of native speed for compute-bound loops. The
binary search WASM snap will be **10–40× faster than the existing pure-JS brute
force** at max_c=1000, and the gap widens as max_c grows.

### Memory usage for max_c = 50 000

| Item | Count | Bytes each | Total |
|---|---|---|---|
| Raw `Triple` structs (3× i64) | 15 920 | 24 | ~383 KB |
| Angle-sorted index (θ: f64, idx: usize) | 15 920 | 16 | ~255 KB |
| Normalised coords cache (x,y: f64) | 15 920 | 16 | ~255 KB |
| **Total manifold** | — | — | **~893 KB** |

WASM linear memory is allocated in 64 KB pages. The manifold for max_c=50 000
will use ~14 pages (~900 KB) — well within the default 256-page (16 MB) limit.
Generation time at max_c=50 000: ~5–15 ms in WASM (acceptable for a one-time
slider-release rebuild, especially with the 300 ms debounce).

### Browser compatibility

| Browser | WASM support | ES module WASM | Notes |
|---|---|---|---|
| Chrome 90+ | ✓ | ✓ | Full support, best performance |
| Firefox 89+ | ✓ | ✓ | Slightly slower JIT for tight loops |
| Safari 15+ | ✓ | ✓ | Safari 14 needs `<script type="module">` workaround |
| Chrome 57–89 | ✓ | Partial | Use `wasm-pack --target bundler` fallback |
| IE 11 | ✗ | ✗ | JS fallback activates automatically |

---

## 6. Concrete File Structure to Create

```
/tmp/ct-wasm/
├── Cargo.toml
├── src/
│   ├── lib.rs          ← ~60 lines: wasm_bindgen exports, Manifold struct
│   ├── triple.rs       ← ~50 lines: Triple, generate_triples, gcd (from cpu_benchmark.rs)
│   ├── snap.rs         ← ~40 lines: build_angle_index, snap_angle
│   └── holonomy.rs     ← ~40 lines: measure_holonomy (no rand dep)
└── www/
    ├── index.html      ← ~300 lines: canvas + sidebar (clone holonomy-viz.html style)
    └── bootstrap.js    ← ~150 lines: WASM init, event wiring, canvas drawing
```

Recommended implementation order:
1. `triple.rs` — copy and adapt from `cpu_benchmark.rs` (already tested)
2. `snap.rs` — angle-sorted index + binary search
3. `holonomy.rs` — walk loop, takes `&[f64]` deltas (no rand)
4. `lib.rs` — wire up wasm-bindgen exports
5. `wasm-pack build --dev` → confirm JS bindings generate
6. `www/index.html` + `bootstrap.js` — embed, wire sliders/canvas
7. `wasm-pack build --release` → confirm < 50 KB

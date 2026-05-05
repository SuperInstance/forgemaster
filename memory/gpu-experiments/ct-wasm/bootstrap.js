/**
 * bootstrap.js — WASM loader and UI wiring for the Constraint Theory demo.
 *
 * The module tries to load the wasm-pack output from ../pkg/ct_wasm.js.
 * If WebAssembly is unavailable or the build hasn't been run yet, it falls
 * back to a pure-JS implementation of the core algorithms.
 */

// ─── JS fallback implementation ─────────────────────────────────────────────

function jsGcd(a, b) {
  while (b) { const t = b; b = a % b; a = t; }
  return a;
}

function jsGenerateTriples(maxC) {
  const out = [];
  const mMax = Math.floor(Math.sqrt(maxC)) + 1;
  for (let m = 2; m <= mMax; m++) {
    for (let n = 1; n < m; n++) {
      if ((m + n) % 2 === 0) continue;
      if (jsGcd(m, n) !== 1) continue;
      const a0 = m * m - n * n, b0 = 2 * m * n, c0 = m * m + n * n;
      if (c0 > maxC) continue;
      for (let k = 1; k * c0 <= maxC; k++) {
        const a = k * a0, b = k * b0, c = k * c0;
        out.push({ a, b, c, x: a / c, y: b / c, angle: Math.atan2(b / c, a / c) });
        if (a !== b)
          out.push({ a: b, b: a, c, x: b / c, y: a / c, angle: Math.atan2(a / c, b / c) });
      }
    }
  }
  out.sort((p, q) => p.angle - q.angle);
  return out;
}

function jsSnap(triples, qx, qy) {
  let best = 0, bestD = Infinity;
  for (let i = 0; i < triples.length; i++) {
    const dx = triples[i].x - qx, dy = triples[i].y - qy;
    const d = dx * dx + dy * dy;
    if (d < bestD) { bestD = d; best = i; }
  }
  return best;
}

function jsMeasureHolonomy(triples, deltas) {
  if (!triples.length || !deltas.length) return 0;
  const si = jsSnap(triples, 1, 0);
  const sx = triples[si].x, sy = triples[si].y;
  let angle = 0, ex = sx, ey = sy;
  for (const d of deltas) {
    angle += d;
    const idx = jsSnap(triples, Math.cos(angle), Math.sin(angle));
    ex = triples[idx].x; ey = triples[idx].y;
  }
  return Math.hypot(ex - sx, ey - sy);
}

// ─── Adapter: wraps either WASM Manifold or JS fallback behind one API ───────

class ManifoldAdapter {
  constructor(wasmManifold, jsTriples) {
    this._wasm = wasmManifold;    // null if using JS fallback
    this._js   = jsTriples;       // null if using WASM
  }

  get length() {
    return this._wasm ? this._wasm.len() : this._js.length;
  }

  snap(qx, qy) {
    return this._wasm ? this._wasm.snap(qx, qy) : jsSnap(this._js, qx, qy);
  }

  tripleAt(idx) {
    if (this._wasm) {
      const arr = this._wasm.triple_at(idx);
      return { a: arr[0], b: arr[1], c: arr[2] };
    }
    return this._js[idx] || { a: 0, b: 0, c: 0 };
  }

  pointAt(idx) {
    if (this._wasm) {
      const arr = this._wasm.point_at(idx);
      return { x: arr[0], y: arr[1] };
    }
    const t = this._js[idx];
    return t ? { x: t.x, y: t.y } : { x: 0, y: 0 };
  }

  allPoints() {
    if (this._wasm) return this._wasm.all_points();
    const pts = new Float64Array(this._js.length * 2);
    for (let i = 0; i < this._js.length; i++) {
      pts[2 * i]     = this._js[i].x;
      pts[2 * i + 1] = this._js[i].y;
    }
    return pts;
  }

  measureHolonomy(deltas) {
    if (this._wasm) return this._wasm.measure_holonomy(Array.from(deltas));
    return jsMeasureHolonomy(this._js, deltas);
  }

  // Returns { bsMs, bfMs, n } — raw timing from JS for accurate Mqps
  benchmark(n) {
    if (this._wasm) {
      const t0 = performance.now();
      this._wasm.bench_snap(n);
      const bsMs = performance.now() - t0;

      const t1 = performance.now();
      this._wasm.bench_snap_brute(n);
      const bfMs = performance.now() - t1;
      return { bsMs, bfMs, n };
    }
    // JS fallback: time brute-force snap (no binary-search variant in pure JS)
    let seed = 0xDEADBEEF;
    const lcg = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 0xFFFFFFFF; };
    const t0 = performance.now();
    for (let i = 0; i < n; i++) jsSnap(this._js, lcg() * 2 - 1, lcg() * 2 - 1);
    const bfMs = performance.now() - t0;
    return { bsMs: bfMs, bfMs, n }; // no separate binary-search in JS fallback
  }

  free() {
    if (this._wasm) { try { this._wasm.free(); } catch (_) {} }
  }
}

// ─── Canvas drawing helpers ──────────────────────────────────────────────────

const COLORS = {
  bg:      '#0d1117',
  circle:  '#30363d',
  dot:     '#238636',
  dotHi:   '#58a6ff',
  snap:    '#58a6ff',
  click:   '#f0883e',
  path:    '#bc8cff',
  text:    '#e6edf3',
  dim:     '#8b949e',
  grid:    '#161b22',
};

export class Demo {
  constructor(canvas, sidebar) {
    this.canvas   = canvas;
    this.ctx      = canvas.getContext('2d');
    this.sidebar  = sidebar;
    this.manifold = null;
    this.useWasm  = false;

    // State
    this.lastClick  = null;   // { qx, qy }
    this.snapResult = null;   // { idx, pt, triple }
    this.pathMode   = false;
    this.pathAngles = [];     // cumulative angles of path clicks
    this.holonomy   = null;   // last holonomy value
  }

  // ── Initialise manifold ──────────────────────────────────────────────────

  async init(maxC) {
    await this._loadManifold(maxC);
    this._draw();
  }

  async _loadManifold(maxC) {
    // Try WASM first
    if (typeof WebAssembly !== 'undefined') {
      try {
        const mod = await import('../pkg/ct_wasm.js');
        await mod.default(); // init() — fetches the .wasm file
        const wm = new mod.Manifold(maxC);
        if (this.manifold) this.manifold.free();
        this.manifold = new ManifoldAdapter(wm, null);
        this.useWasm  = true;
        this._setBadge(`WASM · ${this.manifold.length} triples`);
        return;
      } catch (e) {
        console.warn('WASM load failed, using JS fallback:', e.message || e);
      }
    } else {
      console.warn('WebAssembly not supported — using JS fallback');
    }

    // JS fallback
    const ts = jsGenerateTriples(maxC);
    if (this.manifold) this.manifold.free();
    this.manifold = new ManifoldAdapter(null, ts);
    this.useWasm  = false;
    this._setBadge(`JS fallback · ${ts.length} triples`);
  }

  async rebuild(maxC) {
    await this._loadManifold(maxC);
    this.snapResult = null;
    this.pathAngles = [];
    this.holonomy   = null;
    this._draw();
  }

  // ── Interaction ──────────────────────────────────────────────────────────

  handleClick(offsetX, offsetY) {
    if (!this.manifold) return;
    const { qx, qy } = this._canvasToNorm(offsetX, offsetY);

    if (this.pathMode) {
      this._addPathPoint(qx, qy);
    } else {
      this.lastClick  = { qx, qy };
      const idx       = this.manifold.snap(qx, qy);
      const pt        = this.manifold.pointAt(idx);
      const triple    = this.manifold.tripleAt(idx);
      const dist      = Math.hypot(qx - pt.x, qy - pt.y);
      this.snapResult = { idx, pt, triple, dist, qx, qy };
      this._updateSnapInfo(triple, dist);
    }
    this._draw();
  }

  enterPathMode() {
    this.pathMode   = true;
    this.pathAngles = [];
    this.holonomy   = null;
    this._draw();
  }

  closePath() {
    if (this.pathAngles.length < 2) return;
    // Build delta array that closes the path back to start
    const deltas = new Float64Array(this.pathAngles.length);
    for (let i = 0; i < this.pathAngles.length - 1; i++)
      deltas[i] = this.pathAngles[i + 1] - this.pathAngles[i];
    deltas[deltas.length - 1] = -this.pathAngles[this.pathAngles.length - 1];
    this.holonomy = this.manifold.measureHolonomy(deltas);
    this.pathMode = false;
    this._draw();
    return this.holonomy;
  }

  clearPath() {
    this.pathMode   = false;
    this.pathAngles = [];
    this.holonomy   = null;
    this._draw();
  }

  async runBenchmark(n) {
    const { bsMs, bfMs } = this.manifold.benchmark(n);
    const bsMqps = n / bsMs / 1000;
    const bfMqps = n / bfMs / 1000;
    return { bsMqps, bfMqps, speedup: bsMqps / bfMqps };
  }

  // ── Drawing ──────────────────────────────────────────────────────────────

  _draw() {
    const cv  = this.canvas;
    const ctx = this.ctx;
    const W   = cv.width, H = cv.height;
    const cx  = W / 2, cy = H / 2;
    const R   = Math.min(W, H) * 0.44;

    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = COLORS.bg;
    ctx.fillRect(0, 0, W, H);

    // Grid lines
    ctx.strokeStyle = COLORS.grid;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(cx, 0); ctx.lineTo(cx, H);
    ctx.moveTo(0, cy); ctx.lineTo(W, cy);
    ctx.stroke();

    // Unit circle
    ctx.strokeStyle = COLORS.circle;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(cx, cy, R, 0, 2 * Math.PI);
    ctx.stroke();

    // Axis labels
    ctx.fillStyle = COLORS.dim;
    ctx.font = '11px monospace';
    ctx.fillText('(1,0)', cx + R + 4, cy + 4);
    ctx.fillText('(0,1)', cx + 2, cy - R - 4);

    // All triple points
    if (this.manifold) {
      const pts = this.manifold.allPoints();
      ctx.fillStyle = COLORS.dot;
      for (let i = 0; i < pts.length; i += 2) {
        const px = cx + pts[i] * R;
        const py = cy - pts[i + 1] * R;
        ctx.beginPath();
        ctx.arc(px, py, 2, 0, 2 * Math.PI);
        ctx.fill();
      }
    }

    // Snap result
    if (this.snapResult) {
      const { qx, qy, pt, dist } = this.snapResult;
      const epsilon = window._epsilon || 0.02;

      // Click point
      const cpx = cx + qx * R, cpy = cy - qy * R;
      ctx.strokeStyle = COLORS.click;
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(cx, cy); ctx.lineTo(cpx, cpy);
      ctx.stroke();
      ctx.setLineDash([]);

      ctx.fillStyle = COLORS.click;
      ctx.beginPath();
      ctx.arc(cpx, cpy, 4, 0, 2 * Math.PI);
      ctx.fill();

      // Snap point
      const spx = cx + pt.x * R, spy = cy - pt.y * R;
      ctx.strokeStyle = dist > epsilon ? '#f85149' : COLORS.snap;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(cpx, cpy); ctx.lineTo(spx, spy);
      ctx.stroke();

      ctx.fillStyle = COLORS.dotHi;
      ctx.beginPath();
      ctx.arc(spx, spy, 6, 0, 2 * Math.PI);
      ctx.fill();
    }

    // Path overlay
    if (this.pathAngles.length > 0 || this.pathMode) {
      this._drawPath(cx, cy, R);
    }

    // Path mode cursor hint
    if (this.pathMode) {
      ctx.fillStyle = COLORS.path;
      ctx.font = '13px monospace';
      ctx.fillText(`Path mode — ${this.pathAngles.length} point(s)`, 10, H - 10);
    }
  }

  _drawPath(cx, cy, R) {
    const ctx = this.ctx;
    const n   = this.pathAngles.length;
    if (n < 1) return;

    ctx.strokeStyle = COLORS.path;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    for (let i = 0; i < n; i++) {
      const a = this.pathAngles[i];
      const px = cx + Math.cos(a) * R, py = cy - Math.sin(a) * R;
      if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
    }
    if (!this.pathMode && this.holonomy !== null) {
      // Close the path visually
      const a0 = this.pathAngles[0];
      ctx.lineTo(cx + Math.cos(a0) * R, cy - Math.sin(a0) * R);
    }
    ctx.stroke();

    // Draw snap dots along path
    for (let i = 0; i < n; i++) {
      const a = this.pathAngles[i];
      const t = i / Math.max(n - 1, 1);
      const r = Math.round(80 + t * 175), g = Math.round(200 - t * 150), b = 100;
      ctx.fillStyle = `rgb(${r},${g},${b})`;
      ctx.beginPath();
      ctx.arc(cx + Math.cos(a) * R, cy - Math.sin(a) * R, 5, 0, 2 * Math.PI);
      ctx.fill();
    }
  }

  // ── Coordinate helpers ───────────────────────────────────────────────────

  _canvasToNorm(ox, oy) {
    const W = this.canvas.width, H = this.canvas.height;
    const R = Math.min(W, H) * 0.44;
    return {
      qx: (ox - W / 2) / R,
      qy: -(oy - H / 2) / R,   // canvas y is down, maths y is up
    };
  }

  _addPathPoint(qx, qy) {
    const angle = Math.atan2(qy, qx);
    this.pathAngles.push(angle);
  }

  // ── Sidebar helpers ──────────────────────────────────────────────────────

  _setBadge(text) {
    const el = document.getElementById('wasm-badge');
    if (el) el.textContent = text;
  }

  _updateSnapInfo(triple, dist) {
    const el = document.getElementById('snap-info');
    if (!el) return;
    el.innerHTML =
      `<div><span class="label">a</span> <span class="val">${triple.a}</span></div>` +
      `<div><span class="label">b</span> <span class="val">${triple.b}</span></div>` +
      `<div><span class="label">c</span> <span class="val">${triple.c}</span></div>` +
      `<div><span class="label">dist</span> <span class="val">${dist.toExponential(3)}</span></div>`;
  }
}

// ─── Float-drift demo (pure JS, no WASM needed) ──────────────────────────────

export function floatDriftDemo(iterations = 1_000_000) {
  let x = 1.0;
  const f = Math.PI / 3.0;
  for (let i = 0; i < iterations; i++) { x *= f; x /= f; }
  return { rawError: Math.abs(x - 1.0), snapError: 0 };
}

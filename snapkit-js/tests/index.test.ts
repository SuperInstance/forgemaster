import {
  // Eisenstein core
  EisensteinInteger,
  toComplex,
  normSquared,
  magnitude,
  add,
  sub,
  mul,
  conjugate,
  eisensteinRoundNaive,
  eisensteinRound,
  eisensteinSnap,
  eisensteinSnapBatch,
  eisensteinDistance,
  eisensteinFundamentalDomain,
  // Voronoï
  eisensteinToReal,
  snapDistance,
  eisensteinSnapVoronoi,
  eisensteinSnapNaiveVoronoi,
  eisensteinSnapBatchVoronoi,
  // Temporal
  BeatGrid,
  TemporalSnap,
  // Spectral
  entropy,
  autocorrelation,
  hurstExponent,
  spectralSummary,
  spectralBatch,
} from "../src/index.js";

let passed = 0;
let failed = 0;

function assert(condition: boolean, label: string): void {
  if (condition) {
    passed++;
  } else {
    failed++;
    console.error(`  FAIL: ${label}`);
  }
}

function assertClose(actual: number, expected: number, tol: number, label: string): void {
  assert(Math.abs(actual - expected) <= tol, `${label} — got ${actual}, expected ${expected} (±${tol})`);
}

function section(name: string): void {
  console.log(`\n── ${name} ${"─".repeat(Math.max(0, 60 - name.length))}`);
}

// =========================================================================
// Voronoï snap
// =========================================================================
section("Voronoi snap");

{
  const [a, b] = eisensteinSnapVoronoi(0.0, 0.0);
  assert(a === 0 && b === 0, "origin snaps to (0,0)");

  const [a2, b2] = eisensteinSnapVoronoi(1.0, 0.0);
  assert(a2 === 1 && b2 === 0, "(1,0) snaps to (1,0)");

  // Covering radius guarantee: any point within unit hex
  const [a3, b3] = eisensteinSnapVoronoi(0.3, 0.3);
  const dist = snapDistance(0.3, 0.3, a3, b3);
  assertClose(dist, 0, 0.5774, "covering radius ≤ 1/√3"); // 1/√3 ≈ 0.5774

  // Batch
  const batch = eisensteinSnapBatchVoronoi([[0, 0], [1, 0], [0.5, 0.866]]);
  assert(batch.length === 3, "batch returns 3 results");
  assert(batch[0][0] === 0 && batch[0][1] === 0, "batch[0] = (0,0)");
}

// =========================================================================
// Eisenstein integer
// =========================================================================
section("EisensteinInteger");

{
  const e = EisensteinInteger(3, 2);
  assert(e.a === 3 && e.b === 2, "factory sets a, b");
  assert(Object.isFrozen(e), "frozen object");

  // toComplex
  const [x, y] = toComplex(e);
  assertClose(x, 3 - 1, 1e-10, "toComplex real");
  assertClose(y, Math.sqrt(3), 1e-10, "toComplex imag");

  // normSquared
  assertClose(normSquared(EisensteinInteger(1, 0)), 1, 1e-10, "norm(1,0) = 1");
  assertClose(normSquared(EisensteinInteger(0, 1)), 1, 1e-10, "norm(0,1) = 1");
  assertClose(normSquared(EisensteinInteger(1, 1)), 1, 1e-10, "norm(1,1) = 1");

  // magnitude
  assertClose(magnitude(EisensteinInteger(1, 0)), 1, 1e-10, "|1| = 1");

  // add / sub / mul
  const sum_ = add(EisensteinInteger(1, 2), EisensteinInteger(3, 4));
  assert(sum_.a === 4 && sum_.b === 6, "add (1,2)+(3,4) = (4,6)");

  const diff = sub(EisensteinInteger(3, 4), EisensteinInteger(1, 2));
  assert(diff.a === 2 && diff.b === 2, "sub (3,4)-(1,2) = (2,2)");

  const prod = mul(EisensteinInteger(1, 1), EisensteinInteger(1, 0));
  assert(prod.a === 1 && prod.b === 1, "mul (1,1)*(1,0) = (1,1)");

  // conjugate
  const conj = conjugate(EisensteinInteger(3, 2));
  assert(conj.a === 5 && conj.b === -2, "conjugate (3,2) = (5,-2)");
}

// =========================================================================
// Eisenstein rounding
// =========================================================================
section("Eisenstein rounding");

{
  const naive = eisensteinRoundNaive(0.4, 0.2);
  assert(naive.a === 0 && naive.b === 0, "naive round (0.4, 0.2) → (0,0)");

  const vor = eisensteinRound(0.4, 0.2);
  assert(vor.a === 0 && vor.b === 0, "voronoï round (0.4, 0.2) → (0,0)");

  // eisensteinToReal roundtrip
  const [x, y] = eisensteinToReal(1, 0);
  const rt = eisensteinRound(x, y);
  assert(rt.a === 1 && rt.b === 0, "roundtrip (1,0)");
}

// =========================================================================
// Eisenstein snap
// =========================================================================
section("Eisenstein snap");

{
  const snap = eisensteinSnap(0.01, 0.01);
  assertClose(snap.distance, 0, 0.05, "snap near origin is close");
  assert(snap.isSnap, "near-origin is a snap");

  const farSnap = eisensteinSnap(100.7, 200.3);
  assert(farSnap.nearest.a !== undefined, "far snap produces result");

  // Batch
  const batch = eisensteinSnapBatch([[0, 0], [1, 0], [0.5, 0.866]]);
  assert(batch.length === 3, "batch snap returns 3");
  assert(batch[0].isSnap, "batch[0] is snap");

  // Distance
  const d = eisensteinDistance(0, 0, 1, 0);
  assertClose(d, 1, 0.01, "distance between adjacent lattice points ≈ 1");
}

// =========================================================================
// Fundamental domain
// =========================================================================
section("Fundamental domain");

{
  const [unit, reduced] = eisensteinFundamentalDomain(3, 0);
  assert(unit.a !== undefined, "fundamental domain returns unit");
  assert(reduced.a !== undefined, "fundamental domain returns reduced");
}

// =========================================================================
// BeatGrid
// =========================================================================
section("BeatGrid");

{
  const grid = new BeatGrid(1.0, 0.0, 0.0);

  // Nearest beat
  const [bt, idx] = grid.nearestBeat(0.3);
  assertClose(bt, 0.0, 1e-10, "nearest beat to 0.3 is 0");
  assert(idx === 0, "beat index 0");

  const [bt2, idx2] = grid.nearestBeat(1.6);
  assertClose(bt2, 2.0, 1e-10, "nearest beat to 1.6 is 2");
  assert(idx2 === 2, "beat index 2");

  // Snap
  const snap = grid.snap(1.05, 0.1);
  assertClose(snap.snappedTime, 1.0, 1e-10, "snap 1.05 → 1.0");
  assert(snap.isOnBeat, "1.05 is on-beat with tolerance 0.1");
  assertClose(snap.beatPhase, 0.05, 0.01, "beat phase ≈ 0.05");

  const snapOff = grid.snap(1.5, 0.1);
  assert(!snapOff.isOnBeat, "1.5 is off-beat with tolerance 0.1");

  // Batch
  const batch = grid.snapBatch([0.05, 1.05, 2.05], 0.1);
  assert(batch.length === 3, "batch snap 3");
  assert(batch[0].isOnBeat, "batch[0] on-beat");

  // beatsInRange
  const beats = grid.beatsInRange(0.5, 3.5);
  assert(beats.length === 3, "3 beats in [0.5, 3.5)");
  assertClose(beats[0], 1.0, 1e-10, "first beat = 1.0");
  assertClose(beats[2], 3.0, 1e-10, "last beat = 3.0");

  // Error on bad period
  let threw = false;
  try { new BeatGrid(0); } catch { threw = true; }
  assert(threw, "BeatGrid throws on period=0");

  threw = false;
  try { new BeatGrid(-1); } catch { threw = true; }
  assert(threw, "BeatGrid throws on period=-1");

  // Empty range
  assert(new BeatGrid(1).beatsInRange(5, 3).length === 0, "empty beats range");
}

// =========================================================================
// TemporalSnap
// =========================================================================
section("TemporalSnap");

{
  const grid = new BeatGrid(1.0, 0.0, 0.0);
  const ts = new TemporalSnap(grid, 0.1, 0.05, 3);

  // No T-0 with insufficient history
  const r1 = ts.observe(0.0, 0.1);
  assert(!r1.isTMinus0, "no T-0 with 1 sample");

  // T-0 detection: value crosses zero with sign change
  ts.observe(0.5, 0.3);   // rising
  ts.observe(1.0, -0.1);  // past zero
  ts.observe(1.5, -0.3);  // still negative — not T-0 (|currVal| > threshold)

  ts.reset();
  ts.observe(0.0, 0.3);
  ts.observe(0.5, 0.1);
  ts.observe(1.0, -0.01);  // crosses zero, small |val|
  const r2 = ts.observe(1.5, -0.1);
  // The T-0 flag depends on the current observation being the one at zero

  // History
  const hist = ts.history;
  assert(hist.length === 4, "history has 4 entries");

  // Reset
  ts.reset();
  assert(ts.history.length === 0, "history cleared after reset");
}

// =========================================================================
// Entropy
// =========================================================================
section("Entropy");

{
  // Uniform distribution → high entropy
  const uniform = Array.from({ length: 100 }, (_, i) => i);
  const h = entropy(uniform, 10);
  assert(h > 2.0, `uniform entropy > 2 bits (got ${h.toFixed(3)})`);

  // Constant → 0 entropy
  assertClose(entropy([1, 1, 1, 1], 10), 0, 1e-10, "constant entropy = 0");

  // Too few samples
  assertClose(entropy([1], 10), 0, 1e-10, "single point entropy = 0");
}

// =========================================================================
// Autocorrelation
// =========================================================================
section("Autocorrelation");

{
  // Lag 0 always 1
  const acf = autocorrelation([1, 2, 3, 4, 5]);
  assertClose(acf[0], 1.0, 1e-10, "acf[0] = 1");

  // Constant signal
  const acfConst = autocorrelation([5, 5, 5, 5]);
  assertClose(acfConst[0], 1.0, 1e-10, "constant acf[0] = 1");

  // Single element
  const acf1 = autocorrelation([42]);
  assert(acf1.length === 1 && acf1[0] === 1.0, "single element acf = [1]");

  // maxLag control
  const acf3 = autocorrelation([1, 2, 3, 4, 5, 6, 7, 8], 2);
  assert(acf3.length === 3, "maxLag=2 gives 3 values");
}

// =========================================================================
// Hurst exponent
// =========================================================================
section("Hurst exponent");

{
  // iid noise → H ≈ 0.5
  const noise: number[] = [];
  for (let i = 0; i < 5000; i++) noise.push(Math.random());
  const h = hurstExponent(noise);
  assert(h >= 0.3 && h <= 0.7, `iid noise Hurst ≈ 0.5 (got ${h.toFixed(3)})`);

  // Too few points → default 0.5
  assertClose(hurstExponent([1, 2, 3]), 0.5, 1e-10, "short series → 0.5");
}

// =========================================================================
// Spectral summary
// =========================================================================
section("Spectral summary");

{
  const data = Array.from({ length: 200 }, (_, i) => Math.sin(i * 0.1) + Math.random() * 0.1);
  const summary = spectralSummary(data);
  assert(typeof summary.entropyBits === "number", "entropyBits is number");
  assert(typeof summary.hurst === "number", "hurst is number");
  assert(typeof summary.autocorrLag1 === "number", "autocorrLag1 is number");
  assert(typeof summary.autocorrDecay === "number", "autocorrDecay is number");
  assert(typeof summary.isStationary === "boolean", "isStationary is boolean");
  assert(Object.isFrozen(summary), "summary is frozen");

  // Batch
  const batch = spectralBatch([data, data]);
  assert(batch.length === 2, "batch spectral returns 2");
  assertClose(batch[0].entropyBits, batch[1].entropyBits, 1e-10, "batch results identical");
}

// =========================================================================
// Summary
// =========================================================================
console.log(`\n${"═".repeat(64)}`);
console.log(`  Results: ${passed} passed, ${failed} failed`);
console.log(`${"═".repeat(64)}\n`);

if (failed > 0) {
  process.exit(1);
}

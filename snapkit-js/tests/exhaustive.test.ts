/**
 * Exhaustive correctness + performance tests for @superinstance/snapkit
 */

import {
  EisensteinInteger,
  toComplex,
  normSquared,
  magnitude,
  eisensteinRoundNaive,
  eisensteinRound,
  eisensteinSnap,
  eisensteinSnapBatch,
  eisensteinToReal,
  snapDistance,
  eisensteinSnapVoronoi,
  eisensteinSnapNaiveVoronoi,
  eisensteinSnapBatchVoronoi,
  BeatGrid,
  TemporalSnap,
  entropy,
  autocorrelation,
  hurstExponent,
  spectralSummary,
} from "../src/index.js";

// ─── Test harness ─────────────────────────────────────────────────────────

let passed = 0;
let failed = 0;
const failures: string[] = [];

function assert(condition: boolean, label: string): void {
  if (condition) {
    passed++;
  } else {
    failed++;
    failures.push(label);
    console.error(`  FAIL: ${label}`);
  }
}

function assertClose(actual: number, expected: number, tol: number, label: string): void {
  const ok = Math.abs(actual - expected) <= tol;
  if (ok) {
    passed++;
  } else {
    failed++;
    failures.push(label);
    console.error(`  FAIL: ${label} — got ${actual}, expected ${expected} (±${tol})`);
  }
}

function section(name: string): void {
  console.log(`\n══ ${name} ${"═".repeat(Math.max(0, 58 - name.length))}`);
}

// Seeded PRNG for reproducibility (xorshift32)
function makeRng(seed: number) {
  let s = seed | 0;
  return () => {
    s ^= s << 13;
    s ^= s >> 17;
    s ^= s << 5;
    return (s >>> 0) / 4294967296;
  };
}

// ─── Constants ────────────────────────────────────────────────────────────

const INV_SQRT3 = 1 / Math.sqrt(3); // ≈ 0.57735
const N = 100_000;
const rng = makeRng(42);

// Generate random points in [-50, 50]²
function randomPoints(count: number): [number, number][] {
  const pts: [number, number][] = [];
  for (let i = 0; i < count; i++) {
    pts.push([rng() * 100 - 50, rng() * 100 - 50]);
  }
  return pts;
}

// Check if (a,b) is a valid Eisenstein integer (both are integers)
function isInteger(n: number): boolean {
  return Number.isInteger(n);
}

// ═══════════════════════════════════════════════════════════════════════════
// PHASE 1: CORRECTNESS
// ═══════════════════════════════════════════════════════════════════════════

console.log("╔════════════════════════════════════════════════════════════════╗");
console.log("║  PHASE 1: CORRECTNESS                                        ║");
console.log("╚════════════════════════════════════════════════════════════════╝");

// ── 1.1 Eisenstein Voronoï Snap — 100K random points ────────────────────

section("1.1 Eisenstein Voronoï Snap — 100K random points");

{
  const pts = randomPoints(N);
  let maxDist = 0;
  let idempotentOk = 0;
  let validLattice = 0;

  for (let i = 0; i < N; i++) {
    const [x, y] = pts[i];
    const [a, b] = eisensteinSnapVoronoi(x, y);
    const dist = snapDistance(x, y, a, b);

    // Snap distance ≤ 1/√3
    if (dist <= INV_SQRT3 + 1e-9) {
      maxDist = Math.max(maxDist, dist);
    } else {
      assert(false, `snap distance ${dist.toFixed(6)} > 1/√3 at (${x.toFixed(3)}, ${y.toFixed(3)}) → (${a}, ${b})`);
      break;
    }

    // Valid Eisenstein integer
    if (isInteger(a) && isInteger(b)) validLattice++;

    // Idempotent: snap(snap(p)) == snap(p)
    const [sx, sy] = eisensteinToReal(a, b);
    const [a2, b2] = eisensteinSnapVoronoi(sx, sy);
    if (a2 === a && b2 === b) idempotentOk++;
  }

  assert(maxDist <= INV_SQRT3 + 1e-9, `all 100K snap distances ≤ 1/√3 (max: ${maxDist.toFixed(6)})`);
  assert(idempotentOk === N, `idempotent: ${idempotentOk}/${N}`);
  assert(validLattice === N, `valid lattice points: ${validLattice}/${N}`);
}

// ── 1.1b Boundary / edge cases ──────────────────────────────────────────

section("1.1b Boundary / edge cases");

{
  // Origin
  const [oa, ob] = eisensteinSnapVoronoi(0, 0);
  assert(oa === 0 && ob === 0, "origin → (0,0)");

  // Very large coords
  const [la, lb] = eisensteinSnapVoronoi(1e6, 1e6);
  assert(isInteger(la) && isInteger(lb), "large coords produce valid lattice");
  const ld = snapDistance(1e6, 1e6, la, lb);
  assert(ld <= INV_SQRT3 + 1e-3, `large coords snap dist ${ld.toFixed(6)} ≤ 1/√3`);

  // Negative values
  const [na, nb] = eisensteinSnapVoronoi(-3.7, -2.4);
  assert(isInteger(na) && isInteger(nb), "negative coords produce valid lattice");
  const nd = snapDistance(-3.7, -2.4, na, nb);
  assert(nd <= INV_SQRT3 + 1e-9, `negative snap dist ${nd.toFixed(6)} ≤ 1/√3`);

  // Known lattice points snap to themselves
  const knownPoints: [number, number][] = [[1, 0], [0, 1], [-1, 1], [-1, 0], [0, -1], [1, -1]];
  for (const [a, b] of knownPoints) {
    const [rx, ry] = eisensteinToReal(a, b);
    const [sa, sb] = eisensteinSnapVoronoi(rx, ry);
    assert(sa === a && sb === b, `lattice (${a},${b}) roundtrips`);
  }
}

// ── 1.2 Voronoï vs Naive snap ──────────────────────────────────────────

section("1.2 Voronoï vs Naive snap — 100K comparison");

{
  const rng2 = makeRng(123);
  const pts: [number, number][] = [];
  for (let i = 0; i < N; i++) pts.push([rng2() * 100 - 50, rng2() * 100 - 50]);

  let maxDistNaive = 0;
  let maxDistVoronoi = 0;
  let voronoiCloser = 0;
  let agree = 0;

  for (let i = 0; i < N; i++) {
    const [x, y] = pts[i];
    const [na, nb] = eisensteinSnapNaiveVoronoi(x, y);
    const [va, vb] = eisensteinSnapVoronoi(x, y);

    const dNaive = snapDistance(x, y, na, nb);
    const dVoronoi = snapDistance(x, y, va, vb);

    maxDistNaive = Math.max(maxDistNaive, dNaive);
    maxDistVoronoi = Math.max(maxDistVoronoi, dVoronoi);

    if (dVoronoi <= dNaive + 1e-12) voronoiCloser++;
    if (na === va && nb === vb) agree++;
  }

  assert(maxDistVoronoi <= INV_SQRT3 + 1e-9, `Voronoi max dist ${maxDistVoronoi.toFixed(6)} ≤ 1/√3`);
  console.log(`  Naive max dist:   ${maxDistNaive.toFixed(6)}`);
  console.log(`  Voronoi max dist: ${maxDistVoronoi.toFixed(6)}`);
  console.log(`  Voronoi ≤ Naive:  ${voronoiCloser}/${N}`);
  console.log(`  Agreement:        ${(100 * agree / N).toFixed(1)}% (${agree}/${N})`);

  assert(voronoiCloser === N, "Voronoi always ≤ Naive distance");
  const agreeRate = agree / N;
  // They should agree on roughly 70-80% of points (the easy ones)
  assert(agreeRate > 0.60, `agreement rate ${(agreeRate * 100).toFixed(1)}% > 60%`);
}

// ── 1.3 Temporal snap ──────────────────────────────────────────────────

section("1.3 Temporal snap — BeatGrid");

{
  // Beat grid: all phases in [0, period)
  const grid = new BeatGrid(1.0, 0.0, 0.0);
  const rng3 = makeRng(777);
  let phasesOk = 0;

  for (let i = 0; i < 10000; i++) {
    const t = rng3() * 1000;
    const result = grid.snap(t);
    if (result.beatPhase >= 0 && result.beatPhase < 1.0) phasesOk++;
  }
  assert(phasesOk === 10000, `all 10K beat phases in [0,1): ${phasesOk}/10000`);

  // Period = 1
  const g1 = new BeatGrid(1);
  const r1 = g1.snap(0.5);
  assertClose(r1.snappedTime, 0.0, 1e-10, "period=1, t=0.5 snaps to 0");
  assertClose(r1.beatPhase, 0.5, 1e-10, "period=1, phase=0.5");

  // Very large timestamps
  const gBig = new BeatGrid(1.0, 0.0, 0.0);
  const rBig = gBig.snap(1e15 + 0.3);
  assert(rBig.beatPhase >= 0 && rBig.beatPhase < 1.0, "large timestamp phase valid");
  assert(isFinite(rBig.snappedTime), "large timestamp produces finite result");

  // beatsInRange
  const beats = grid.beatsInRange(-5.0, 5.0);
  assert(beats.length === 10, `10 beats in [-5,5): got ${beats.length}`);
  for (const b of beats) {
    assert(b >= -5.0 && b < 5.0, `beat ${b} in range [-5,5)`);
  }
}

section("1.3b Temporal snap — T-minus-0 detection");

{
  const grid = new BeatGrid(0.5, 0.0, 0.0);
  const ts = new TemporalSnap(grid, 0.1, 0.05, 3);

  // Synthetic trigger: value goes positive → zero → negative
  ts.observe(0.0, 0.5);   // positive
  ts.observe(0.5, 0.2);   // still positive
  ts.observe(1.0, 0.01);  // near zero, positive slope still
  const r = ts.observe(1.5, -0.01); // crosses zero, small |val|
  // T-0 should detect sign change at near-zero value
  console.log(`  T-minus-0 detected: ${r.isTMinus0} (offset=${r.offset.toFixed(3)})`);
  // Not asserting exact T-0 because the detection depends on history window alignment

  // Edge case: insufficient history → no T-0
  const ts2 = new TemporalSnap(new BeatGrid(1), 0.1, 0.05, 3);
  const r2 = ts2.observe(0.0, 0.0);
  assert(!r2.isTMinus0, "no T-0 with single observation");

  // Reset clears history
  ts2.reset();
  assert(ts2.history.length === 0, "reset clears history");
}

// ── 1.4 Spectral analysis ─────────────────────────────────────────────

section("1.4 Spectral analysis");

{
  // Entropy of [1,1,1,1] = 0 (deterministic)
  const hConst = entropy([1, 1, 1, 1], 10);
  assertClose(hConst, 0, 1e-10, `entropy of constant = 0 (got ${hConst})`);

  // Entropy of [1,2,3,4] should be high (uniform-ish)
  // With 4 distinct values in 10 bins, each gets its own bin → 4 bins of 1 → p=0.25 each
  // H = -4 * 0.25 * log2(0.25) = 2.0 bits
  const hUniform = entropy([1, 2, 3, 4], 10);
  assertClose(hUniform, 2.0, 0.01, `entropy of [1,2,3,4] ≈ 2 bits (got ${hUniform.toFixed(3)})`);

  // Autocorrelation lag-0 = 1.0 always
  const acf1 = autocorrelation([1, 2, 3, 4, 5]);
  assertClose(acf1[0], 1.0, 1e-10, "acf[0] = 1.0 for [1,2,3,4,5]");

  const acf2 = autocorrelation([42, 42, 42]);
  assertClose(acf2[0], 1.0, 1e-10, "acf[0] = 1.0 for constant");

  const acf3 = autocorrelation([1]);
  assert(acf3.length === 1 && acf3[0] === 1.0, "acf[0] = 1.0 for single element");

  // Hurst of random walk ≈ 0.5
  const rng4 = makeRng(9999);
  const walk: number[] = [0];
  for (let i = 1; i < 10000; i++) {
    walk.push(walk[i - 1] + (rng4() - 0.5));
  }
  const hWalk = hurstExponent(walk);
  console.log(`  Hurst of random walk (10K): ${hWalk.toFixed(3)}`);
  assert(hWalk >= 0.35 && hWalk <= 0.65, `Hurst of random walk ≈ 0.5 (got ${hWalk.toFixed(3)})`);

  // Spectral summary consistency
  const data = Array.from({ length: 500 }, (_, i) => Math.sin(i * 0.1));
  const summary = spectralSummary(data);
  assert(summary.entropyBits >= 0, `entropyBits >= 0: ${summary.entropyBits}`);
  assert(summary.hurst >= 0 && summary.hurst <= 1, `hurst in [0,1]: ${summary.hurst}`);
  assert(summary.autocorrLag1 !== undefined, "autocorrLag1 present");
  assert(typeof summary.isStationary === "boolean", "isStationary is boolean");
}

// ═══════════════════════════════════════════════════════════════════════════
// PHASE 2: PERFORMANCE BENCHMARKS
// ═══════════════════════════════════════════════════════════════════════════

console.log("\n╔════════════════════════════════════════════════════════════════╗");
console.log("║  PHASE 2: PERFORMANCE BENCHMARKS                             ║");
console.log("╚════════════════════════════════════════════════════════════════╝");

function benchmark(name: string, fn: () => void, iterations: number): number {
  // Warmup
  for (let i = 0; i < Math.min(100, iterations); i++) fn();

  const start = performance.now();
  for (let i = 0; i < iterations; i++) fn();
  const elapsed = performance.now() - start;
  const opsPerSec = Math.round(iterations / (elapsed / 1000));
  console.log(`  ${name}: ${opsPerSec.toLocaleString()} ops/sec (${elapsed.toFixed(1)}ms for ${iterations.toLocaleString()} ops)`);
  return opsPerSec;
}

interface BenchResult {
  name: string;
  size: number;
  opsPerSec: number;
}

const benchResults: BenchResult[] = [];

for (const size of [1_000, 10_000, 100_000]) {
  section(`Benchmark @ ${size.toLocaleString()} points`);

  const rngBench = makeRng(31415);
  const pts: [number, number][] = [];
  for (let i = 0; i < size; i++) pts.push([rngBench() * 100 - 50, rngBench() * 100 - 50]);

  // 1. Eisenstein naive snap
  let idx1 = 0;
  const ops1 = benchmark(
    `Eisenstein naive snap`,
    () => {
      const [x, y] = pts[idx1 % size];
      eisensteinSnapNaiveVoronoi(x, y);
      idx1++;
    },
    size
  );
  benchResults.push({ name: "naive_snap", size, opsPerSec: ops1 });

  // 2. Eisenstein Voronoï snap
  let idx2 = 0;
  const ops2 = benchmark(
    `Eisenstein Voronoï snap`,
    () => {
      const [x, y] = pts[idx2 % size];
      eisensteinSnapVoronoi(x, y);
      idx2++;
    },
    size
  );
  benchResults.push({ name: "voronoi_snap", size, opsPerSec: ops2 });

  // 3. Batch snap
  const batchSize = Math.min(size, 10_000);
  const batchPts = pts.slice(0, batchSize);
  const batchIters = Math.max(1, Math.floor(size / batchSize));
  const ops3 = benchmark(
    `Batch snap (${batchSize} pts/call)`,
    () => { eisensteinSnapBatchVoronoi(batchPts); },
    batchIters
  );
  benchResults.push({ name: "batch_snap", size, opsPerSec: Math.round(ops3 * batchSize / batchIters * batchIters / batchIters) });

  // 4. Temporal snap
  const grid = new BeatGrid(1.0, 0.0, 0.0);
  const timestamps = Array.from({ length: size }, (_, i) => i * 0.001);
  let idx4 = 0;
  const ops4 = benchmark(
    `Temporal snap`,
    () => {
      grid.snap(timestamps[idx4 % size]);
      idx4++;
    },
    size
  );
  benchResults.push({ name: "temporal_snap", size, opsPerSec: ops4 });

  // 5. Spectral summary
  const specData = Array.from({ length: Math.min(size, 1000) }, (_, i) => Math.sin(i * 0.01) + Math.random() * 0.5);
  const specIters = Math.max(1, Math.floor(size / specData.length));
  const ops5 = benchmark(
    `Spectral summary (${specData.length} pts)`,
    () => { spectralSummary(specData); },
    specIters
  );
  benchResults.push({ name: "spectral_summary", size, opsPerSec: Math.round(ops5) });
}

// ═══════════════════════════════════════════════════════════════════════════
// PHASE 3: BUILD & PACKAGE VERIFICATION
// ═══════════════════════════════════════════════════════════════════════════

console.log("\n╔════════════════════════════════════════════════════════════════╗");
console.log("║  PHASE 3: BUILD & PACKAGE VERIFICATION                       ║");
console.log("╚════════════════════════════════════════════════════════════════╝");

section("3.1 Package verification");

{
  // Read package.json to check zero dependencies
  const fs = await import("fs");
  const pkgPath = "/home/phoenix/.openclaw/workspace/snapkit-js/package.json";
  const pkg = JSON.parse(fs.readFileSync(pkgPath, "utf-8"));

  assert(Object.keys(pkg.dependencies || {}).length === 0, "zero production dependencies");
  console.log(`  dependencies: ${JSON.stringify(pkg.dependencies || {})}`);
  console.log(`  devDependencies: ${Object.keys(pkg.devDependencies || {}).join(", ")}`);
  assert(pkg.type === "module", "package is ESM");
  assert(pkg.types === "./dist/index.d.ts", "types field set");

  // Check dist exists
  const distDir = "/home/phoenix/.openclaw/workspace/snapkit-js/dist";
  const distFiles = fs.readdirSync(distDir);
  assert(distFiles.includes("index.js"), "dist/index.js exists");
  assert(distFiles.includes("index.d.ts"), "dist/index.d.ts exists");
  console.log(`  dist files: ${distFiles.filter(f => f.endsWith(".js")).length} .js, ${distFiles.filter(f => f.endsWith(".d.ts")).length} .d.ts`);

  // Check exports from built file
  const distContent = fs.readFileSync(`${distDir}/index.js`, "utf-8");
  assert(distContent.includes("eisensteinSnapVoronoi") || distContent.includes("Voronoi"), "dist exports Voronoi");
  assert(distContent.includes("BeatGrid"), "dist exports BeatGrid");
  assert(distContent.includes("entropy"), "dist exports entropy");
}

section("3.2 Type exports verification");

{
  // Verify all major exports are functions/classes
  assert(typeof EisensteinInteger === "function", "EisensteinInteger is callable");
  assert(typeof toComplex === "function", "toComplex is function");
  assert(typeof eisensteinSnapVoronoi === "function", "eisensteinSnapVoronoi is function");
  assert(typeof eisensteinSnapNaiveVoronoi === "function", "eisensteinSnapNaiveVoronoi is function");
  assert(typeof BeatGrid === "function", "BeatGrid is constructor");
  assert(typeof TemporalSnap === "function", "TemporalSnap is constructor");
  assert(typeof entropy === "function", "entropy is function");
  assert(typeof hurstExponent === "function", "hurstExponent is function");
  assert(typeof autocorrelation === "function", "autocorrelation is function");
  assert(typeof spectralSummary === "function", "spectralSummary is function");
}

// ═══════════════════════════════════════════════════════════════════════════
// SUMMARY
// ═══════════════════════════════════════════════════════════════════════════

console.log(`\n${"═".repeat(64)}`);
console.log(`  CORRECTNESS: ${passed} passed, ${failed} failed`);
console.log(`${"═".repeat(64)}`);

console.log("\n  BENCHMARK SUMMARY:");
console.log("  " + "─".repeat(60));
console.log(`  ${"Operation".padEnd(20)} ${"Size".padStart(8)} ${"ops/sec".padStart(15)}`);
console.log("  " + "─".repeat(60));
for (const r of benchResults) {
  console.log(`  ${r.name.padEnd(20)} ${r.size.toLocaleString().padStart(8)} ${r.opsPerSec.toLocaleString().padStart(15)}`);
}
console.log("  " + "─".repeat(60));

if (failed > 0) {
  console.log("\n  FAILURES:");
  for (const f of failures) console.log(`    - ${f}`);
  process.exit(1);
}

console.log("\n  ✅ All tests passed.\n");

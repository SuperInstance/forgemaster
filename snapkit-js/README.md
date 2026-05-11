# @superinstance/snapkit

Eisenstein lattice snap, temporal beat-grid alignment, and spectral analysis — zero dependencies, pure TypeScript.

## Install

```bash
npm install @superinstance/snapkit
```

## Quick Start

```typescript
import {
  eisensteinSnap,
  eisensteinRound,
  EisensteinInteger,
  toComplex,
  BeatGrid,
  TemporalSnap,
  entropy,
  hurstExponent,
  spectralSummary,
} from "@superinstance/snapkit";
```

## API Reference

### Eisenstein Lattice

#### `eisensteinRound(x, y) → EisensteinInteger`

Round a Cartesian point to the nearest Eisenstein integer using the 9-candidate Voronoï snap (covering radius ≤ 1/√3).

```typescript
const ei = eisensteinRound(0.3, 0.5);
console.log(ei); // { a: 0, b: 1 }
```

#### `EisensteinInteger(a, b) → EisensteinInteger`

Create a frozen Eisenstein integer value object. Immutable (like Python's `@dataclass(frozen=True, slots=True)`).

```typescript
const e = EisensteinInteger(3, 2);
// e.a === 3, e.b === 2, Object.isFrozen(e) === true
```

#### `toComplex(ei) → [number, number]`

Convert to Cartesian coordinates `[real, imag]`.

#### `normSquared(ei) → number`

Eisenstein norm²: `a² − ab + b²`. Always ≥ 0.

#### `magnitude(ei) → number`

Euclidean magnitude `√(norm²)`.

#### `add(left, right)`, `sub(left, right)`, `mul(left, right)`

Arithmetic on Eisenstein integers.

#### `conjugate(ei) → EisensteinInteger`

Galois conjugate: `(a+b, −b)`.

#### `eisensteinSnap(x, y, tolerance?) → SnapResult`

Snap and report distance + whether within tolerance.

```typescript
const result = eisensteinSnap(0.01, 0.01);
// { nearest: { a: 0, b: 0 }, distance: 0.014, isSnap: true }
```

#### `eisensteinSnapBatch(points, tolerance?) → SnapResult[]`

Vectorized snap.

#### `eisensteinDistance(x1, y1, x2, y2) → number`

Lattice distance between two Cartesian points.

#### `eisensteinFundamentalDomain(x, y) → [EisensteinInteger, EisensteinInteger]`

Reduce to canonical fundamental-domain representative.

### Voronoï Snap (low-level)

```typescript
import { eisensteinSnapVoronoi, snapDistance, eisensteinToReal } from "@superinstance/snapkit";

const [a, b] = eisensteinSnapVoronoi(0.3, 0.7);
const [x, y] = eisensteinToReal(a, b);
const d = snapDistance(0.3, 0.7, a, b);
```

### Temporal

#### `new BeatGrid(period?, phase?, tStart?)`

Periodic grid of time points.

```typescript
const grid = new BeatGrid(1.0); // 1-second beats

const [beatTime, beatIndex] = grid.nearestBeat(2.7);
// beatTime = 3.0, beatIndex = 3

const result = grid.snap(2.05, 0.1);
// { snappedTime: 2.0, isOnBeat: true, beatPhase: 0.05, ... }

const beats = grid.beatsInRange(0.5, 3.5); // [1.0, 2.0, 3.0]
```

#### `new TemporalSnap(grid, tolerance?, t0Threshold?, t0Window?)`

Temporal snap with T-minus-0 (zero-crossing) detection.

```typescript
const ts = new TemporalSnap(grid);
ts.observe(0.0, 0.5);
ts.observe(0.5, 0.2);
const result = ts.observe(1.0, -0.01);
// result.isTMinus0 may be true if zero crossing detected
```

### Spectral

#### `entropy(data, bins?) → number`

Shannon entropy in bits via histogram binning.

```typescript
const h = entropy([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 5);
```

#### `autocorrelation(data, maxLag?) → number[]`

Normalized autocorrelation function.

```typescript
const acf = autocorrelation(mySignal, 20);
// acf[0] === 1.0 always
```

#### `hurstExponent(data) → number`

Hurst exponent via R/S analysis. H ≈ 0.5 → random, H > 0.5 → trending, H < 0.5 → mean-reverting.

```typescript
const H = hurstExponent(stockPrices);
```

#### `spectralSummary(data, bins?, maxLag?) → SpectralSummary`

Complete spectral analysis in one call.

```typescript
const summary = spectralSummary(signal);
// {
//   entropyBits: 3.2,
//   hurst: 0.52,
//   autocorrLag1: 0.95,
//   autocorrDecay: 12,
//   isStationary: false
// }
```

#### `spectralBatch(seriesList, bins?, maxLag?) → SpectralSummary[]`

Vectorized spectral analysis.

## Guarantees

- **Covering radius ≤ 1/√3** — Voronoï snap always finds the true nearest Eisenstein integer
- **Zero dependencies** — pure TypeScript, works in Node.js and browsers
- **Frozen objects** — all return types are `Object.freeze()`d (equivalent to Python's `frozen=True`)
- **ESM + CJS dual output** — works with `import` and `require()`

## Development

```bash
npm install        # install dev deps (tsup, typescript, tsx)
npm test           # run tests
npm run build      # build dist (ESM + CJS + .d.ts)
```

## License

MIT

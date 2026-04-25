# constraint-theory-core v2.0 — Design Document

**Status:** Draft
**Supersedes:** v1.0.1
**Date:** 2026-04-25

---

## Overview

v1.0.1 provided a `PythagoreanManifold` backed by a KD-tree with a fixed `snap` function.
v2.0 generalises the architecture along five axes:

| Feature | v1.0.1 | v2.0 |
|---|---|---|
| Tolerance | fixed ε | adaptive `ε(c) = k/c` |
| Resolution | compile-time | configurable + auto-refinement |
| Diagnostics | none | `SnapReport` per operation |
| Holonomy | none | `HolonomyMeter` API |
| Surfaces | Pythagorean only | open `ConstraintSurface` trait |

The mathematical foundation remains **discrete constraint manifolds**: a lattice of points
(here, Pythagorean triples `(a,b,c)` with `a²+b²=c²`) embedded in a continuous ambient space,
with a projection operator ("snap") that maps ambient points to their nearest lattice point.

---

## 1. AdaptiveTolerance

### Mathematical motivation

In a Pythagorean triple `(a,b,c)`, the hypotenuse `c` grows as `O(√(a²+b²))`.
For large `c`, consecutive triples are spaced further apart — the manifold becomes
**sparse** in that region.  A fixed tolerance ε would either miss valid near-snaps at
large `c`, or admit false positives at small `c`.

The adaptive rule `ε(c) = k / c` normalises tolerance to local triple density:
as `c` grows the gap between triples shrinks relative to `c`, so the absolute
tolerance is relaxed proportionally while the *relative* tolerance stays bounded.

```rust
/// Tolerance policy governing when a point is considered "close enough" to
/// snap onto a manifold point rather than returning `None` / an error.
pub trait TolerancePolicy: Send + Sync {
    /// Return the maximum allowed Euclidean distance for a snap at ambient
    /// coordinate `c` (the hypotenuse magnitude or analogous scale parameter).
    ///
    /// For `AdaptiveTolerance` this is `k / c`; for `FixedTolerance` this
    /// returns a constant.
    fn epsilon(&self, c: f64) -> f64;
}

/// Adaptive tolerance: ε(c) = k / c.
///
/// `k` is a dimensionless stiffness constant.  Larger `k` accepts looser
/// snaps; `k = 1.0` is the canonical unit-normalised policy.
pub struct AdaptiveTolerance {
    /// Stiffness constant `k`.
    pub k: f64,
}

/// Fixed tolerance retained for backward compatibility and unit-testing.
pub struct FixedTolerance {
    pub epsilon: f64,
}

impl TolerancePolicy for AdaptiveTolerance {
    fn epsilon(&self, c: f64) -> f64;
}

impl TolerancePolicy for FixedTolerance {
    fn epsilon(&self, c: f64) -> f64;
}
```

---

## 2. ManifoldResolution

### Mathematical motivation

The number of primitive Pythagorean triples with hypotenuse ≤ N grows as `O(N)`.
At `max_c = 100` there are ~16 primitives; at `max_c = 100_000` there are ~15_916.
Higher resolution means denser KD-tree, finer snap granularity, but quadratic build cost.

**Auto-resolution** starts the tree at low resolution, monitors query hit-rate per
spatial cell, and re-seeds a sub-tree at higher resolution when queries cluster —
a lazy spatial refinement analogous to adaptive mesh refinement (AMR) in PDE solvers.

```rust
/// Resolution configuration for a Pythagorean manifold.
#[derive(Debug, Clone)]
pub struct ResolutionConfig {
    /// Upper bound on hypotenuse `c` used when generating triples.
    /// Controls triple count: ~`max_c / 6` primitive triples exist below `max_c`.
    pub max_c: u64,

    /// Whether to enable automatic spatial refinement.
    /// When `true`, the manifold may internally increase resolution in hot regions.
    pub auto_refine: bool,

    /// Minimum number of queries hitting a spatial cell before triggering
    /// refinement of that cell (only relevant when `auto_refine = true`).
    pub refine_threshold: usize,

    /// Maximum resolution the auto-refiner may grow to (caps unbounded growth).
    pub max_auto_c: u64,
}

impl ResolutionConfig {
    /// Coarse preset: `max_c = 100`, no auto-refinement.
    /// Fast build (~μs), low precision, suitable for real-time preview.
    pub fn low() -> Self;

    /// Medium preset: `max_c = 10_000`, auto-refinement enabled.
    pub fn medium() -> Self;

    /// Fine preset: `max_c = 100_000`, auto-refinement enabled.
    /// Slow build (~ms), high precision, suitable for offline analysis.
    pub fn high() -> Self;
}

/// A Pythagorean manifold with configurable resolution and tolerance.
pub struct PythagoreanManifold {
    /// All triples `(a, b, c)` with `a² + b² = c²`, `a ≤ b`, generated up to
    /// `config.max_c`.  Stored sorted by `c` for cache-friendly iteration.
    pub triples: Vec<(i64, i64, i64)>,

    pub config: ResolutionConfig,

    /// Active tolerance policy.  Boxed to allow runtime selection.
    pub tolerance: Box<dyn TolerancePolicy>,
    // Internal KD-tree omitted from public surface; accessed via `snap`.
}

impl PythagoreanManifold {
    /// Construct a manifold with explicit configuration.
    pub fn new(config: ResolutionConfig, tolerance: Box<dyn TolerancePolicy>) -> Self;

    /// Convenience constructor using `ResolutionConfig::medium()` and
    /// `AdaptiveTolerance { k: 1.0 }`.
    pub fn default() -> Self;

    /// Snap `value` onto the nearest triple, returning a full `SnapReport`.
    /// Returns `Err` if no triple is within tolerance.
    pub fn snap(&self, value: f64) -> Result<SnapReport, SnapError>;

    /// Hint that queries will concentrate around `region_c`.
    /// Triggers preemptive refinement when `auto_refine = true`.
    pub fn hint_region(&mut self, region_c: f64);
}
```

---

## 3. HolonomyMeter

### Mathematical motivation

On a smooth Riemannian manifold, **holonomy** measures the rotational defect
accumulated when parallel-transporting a vector around a closed loop.
On a *discrete* constraint manifold the analogue is the **snap drift**: starting
at a point, apply N incremental angle deltas (summing to 0), snap at each step,
and measure how far the final snapped position differs from the start.

Non-zero displacement reveals the manifold's **curvature signature** in that region:
a flat region has near-zero holonomy; a region near a triple cluster or a gap
accumulates large drift.  This is useful for:
- Detecting numerical instability hotspots in physics simulations.
- Choosing where to increase resolution.
- Validating that a tolerance policy is conservative enough.

```rust
/// A single waypoint in a holonomy traversal path.
#[derive(Debug, Clone)]
pub struct PathPoint {
    /// Ambient (pre-snap) coordinate at this step.
    pub ambient: f64,
    /// Snapped coordinate, or `None` if the snap failed.
    pub snapped: Option<i64>,
    /// Cumulative angle from loop start at this step (radians).
    pub cumulative_angle: f64,
}

/// Result of a closed-loop holonomy measurement.
#[derive(Debug, Clone)]
pub struct HolonomyResult {
    /// Total angle drift accumulated over all snap steps (radians).
    /// Ideally 0.0 for a flat region; non-zero indicates curvature.
    pub total_angle_drift: f64,

    /// Euclidean displacement of the final snapped value from the initial
    /// snapped value.  Zero on a perfectly flat discrete manifold.
    pub final_displacement: f64,

    /// Full sequence of waypoints, length == `steps`.
    pub path_points: Vec<PathPoint>,

    /// Number of steps where snap failed (out-of-tolerance).
    pub failed_snaps: usize,
}

/// Errors that can occur during holonomy measurement.
#[derive(Debug)]
pub enum HolonomyError {
    /// Too many snap failures along the loop to produce a reliable result.
    TooManyFailures { failed: usize, total: usize },
    /// The requested number of steps is too small (minimum 3).
    InsufficientSteps,
}

/// Measures holonomy properties of a constraint manifold.
pub struct HolonomyMeter<'a> {
    /// Reference to the manifold under test.
    pub manifold: &'a PythagoreanManifold,
    /// Random seed for reproducible loop generation.
    pub seed: u64,
}

impl<'a> HolonomyMeter<'a> {
    /// Construct a meter over `manifold` with given RNG seed.
    pub fn new(manifold: &'a PythagoreanManifold, seed: u64) -> Self;

    /// Send a query around a closed loop of `steps` random angle deltas
    /// that sum to exactly zero (constructed via reflection).
    ///
    /// Starting from `start_value`, the loop applies each delta, snaps, then
    /// measures the total drift and final displacement.
    ///
    /// # Parameters
    /// - `steps`: Number of loop waypoints (≥ 3).
    /// - `start_value`: Ambient starting coordinate.
    /// - `delta_magnitude`: RMS magnitude of each angle step (radians).
    pub fn holonomy_loop(
        &self,
        steps: usize,
        start_value: f64,
        delta_magnitude: f64,
    ) -> Result<HolonomyResult, HolonomyError>;

    /// Run `holonomy_loop` over a grid of starting values and return
    /// aggregate statistics useful for choosing resolution/tolerance.
    pub fn survey(
        &self,
        start_values: &[f64],
        steps: usize,
        delta_magnitude: f64,
    ) -> Vec<Result<HolonomyResult, HolonomyError>>;
}
```

---

## 4. SnapReport

### Motivation

Debugging snap behaviour requires more than a scalar result.  `SnapReport` exposes
the full diagnostic context so callers can audit precision, performance, and resolution
choices without instrumenting internals.

```rust
/// Outcome of a single snap operation, bundling the result with diagnostics.
#[derive(Debug, Clone)]
pub struct SnapReport {
    /// The snapped integer value (projected onto the nearest manifold point).
    pub snapped_value: i64,

    /// Euclidean distance from the input to the snapped manifold point.
    /// A value of 0.0 means the input was exactly on the manifold.
    pub distance_to_manifold: f64,

    /// The Pythagorean triple `(a, b, c)` that was snapped to.
    pub nearest_triple: (i64, i64, i64),

    /// Wall-clock time consumed by this snap operation, in microseconds.
    pub time_us: u64,

    /// The `max_c` of the resolution tier used (may be higher than the base
    /// config if auto-refinement promoted this region).
    pub resolution_used: u64,

    /// Whether adaptive tolerance was invoked (i.e. the point was in a
    /// boundary/sparse region and `ε(c)` was applied rather than a fixed ε).
    pub adaptive_tolerance_applied: bool,

    /// The tolerance ε that was actually used for this snap decision.
    pub epsilon_used: f64,
}

/// Reasons a snap can fail.
#[derive(Debug, Clone, PartialEq)]
pub enum SnapError {
    /// No triple within tolerance was found.
    OutOfTolerance {
        input: f64,
        nearest_distance: f64,
        epsilon: f64,
    },
    /// The manifold has no triples (empty — resolution too low or bug).
    EmptyManifold,
}

impl std::fmt::Display for SnapError {}
impl std::error::Error for SnapError {}
```

---

## 5. MultiManifold and ConstraintSurface

### Mathematical motivation

A **constraint surface** is any co-dimension-1 (or higher) subset of an ambient space
equipped with a projection (retraction) operator.  Pythagorean triples are one example;
others include integer lattices, Gaussian integer rings, unit circles, or custom
simulation constraints.

`MultiManifold` composes several surfaces and snaps to the *closest* across all of them,
enabling simultaneous enforcement of multiple geometric constraints — analogous to
intersection of constraint sets in convex optimisation.

```rust
/// A point on a constraint surface, carrying both the projected coordinate
/// and the surface that produced it.
#[derive(Debug, Clone)]
pub struct SurfacePoint {
    /// Projected (snapped) scalar value.
    pub value: f64,
    /// Distance from the original ambient point to this surface point.
    pub distance: f64,
    /// Human-readable identifier for the surface that produced this point.
    pub surface_id: String,
}

/// Errors returned by surface operations.
#[derive(Debug)]
pub enum SurfaceError {
    /// The point is not within the surface's valid domain.
    OutOfDomain { point: f64 },
    /// The surface could not find a valid projection.
    ProjectionFailed { reason: String },
}

/// A discrete or continuous constraint surface that ambient points can be
/// projected onto.
///
/// Implementors must be object-safe: no generic parameters in methods,
/// allowing `Box<dyn ConstraintSurface>` for runtime polymorphism.
pub trait ConstraintSurface: Send + Sync {
    /// Return a stable identifier for this surface (used in `SurfacePoint`
    /// and diagnostic output).
    fn id(&self) -> &str;

    /// Project (snap) `point` onto the nearest point on this surface.
    ///
    /// Returns `Err` if no valid projection exists within tolerance.
    fn snap(&self, point: f64) -> Result<SurfacePoint, SurfaceError>;

    /// Return the unsigned distance from `point` to the nearest surface point.
    ///
    /// Must be consistent with `snap`: `distance(p) == snap(p)?.distance`.
    fn distance(&self, point: f64) -> f64;

    /// Return `true` if `point` lies on the surface within tolerance.
    ///
    /// Equivalent to `distance(point) < tolerance.epsilon(point)` but may be
    /// more efficient for surfaces with analytic membership tests.
    fn is_valid(&self, point: f64) -> bool;

    /// Optional: return a bounding interval `[lo, hi]` within which this
    /// surface has any points.  Used by `MultiManifold` to prune surfaces
    /// before evaluating `snap`.  Return `None` to opt out of pruning.
    fn bounding_interval(&self) -> Option<(f64, f64)> {
        None
    }
}

/// Adapts a `PythagoreanManifold` to the `ConstraintSurface` trait,
/// exposing it as a surface that snaps to hypotenuse values `c`.
pub struct PythagoreanSurface {
    pub manifold: PythagoreanManifold,
}

impl ConstraintSurface for PythagoreanSurface {
    fn id(&self) -> &str;
    fn snap(&self, point: f64) -> Result<SurfacePoint, SurfaceError>;
    fn distance(&self, point: f64) -> f64;
    fn is_valid(&self, point: f64) -> bool;
}

/// Strategy for resolving conflicts when multiple surfaces produce a valid snap.
#[derive(Debug, Clone, PartialEq)]
pub enum ConflictStrategy {
    /// Use the surface with the smallest `distance` (default).
    Nearest,
    /// Use the surface listed first in the `MultiManifold::surfaces` vec.
    Priority,
    /// Return all valid snaps, sorted by distance.
    All,
}

/// A composition of multiple constraint surfaces.
///
/// `snap` evaluates each surface and selects among valid projections
/// according to the configured `ConflictStrategy`.
pub struct MultiManifold {
    /// Ordered list of surfaces.  Order matters when `strategy == Priority`.
    pub surfaces: Vec<Box<dyn ConstraintSurface>>,

    /// How to resolve ties or multiple valid snaps.
    pub strategy: ConflictStrategy,
}

impl MultiManifold {
    /// Construct a multi-manifold with given surfaces and strategy.
    pub fn new(surfaces: Vec<Box<dyn ConstraintSurface>>, strategy: ConflictStrategy) -> Self;

    /// Add a surface at runtime.
    pub fn add_surface(&mut self, surface: Box<dyn ConstraintSurface>);

    /// Remove a surface by its `id()`.  Returns `true` if found and removed.
    pub fn remove_surface(&mut self, id: &str) -> bool;

    /// Snap `point` across all surfaces, applying `ConflictStrategy`.
    ///
    /// Returns `Vec<SurfacePoint>` with one element under `Nearest`/`Priority`,
    /// or all valid snaps under `All`.
    pub fn snap(&self, point: f64) -> Result<Vec<SurfacePoint>, SurfaceError>;

    /// Return the minimum distance from `point` to any surface.
    pub fn min_distance(&self, point: f64) -> f64;
}
```

---

## Type Dependency Graph

```
TolerancePolicy (trait)
  ├─ AdaptiveTolerance
  └─ FixedTolerance

ResolutionConfig
  └─ used by PythagoreanManifold

PythagoreanManifold
  ├─ snap() -> Result<SnapReport, SnapError>
  └─ hint_region()

SnapReport          SnapError
HolonomyResult      HolonomyError
PathPoint

HolonomyMeter<'a>
  └─ borrows &'a PythagoreanManifold

ConstraintSurface (trait)
  └─ PythagoreanSurface (wraps PythagoreanManifold)

MultiManifold
  ├─ Vec<Box<dyn ConstraintSurface>>
  └─ ConflictStrategy
```

---

## Migration from v1.0.1

| v1.0.1 | v2.0 equivalent |
|---|---|
| `PythagoreanManifold { triples }` | `PythagoreanManifold::new(ResolutionConfig::medium(), Box::new(AdaptiveTolerance { k: 1.0 }))` |
| `snap(value, &manifold) -> i64` | `manifold.snap(value).map(|r| r.snapped_value)` |
| Fixed KD-tree | Auto-refining KD-tree per `ResolutionConfig` |

The `snap` free function from v1.0.1 is **removed**; use `PythagoreanManifold::snap`.

---

## Open Questions

1. Should `HolonomyMeter` support non-scalar (2D/3D) ambient spaces?
   Currently scoped to `f64` to match the existing KD-tree.
2. Should `SnapReport::time_us` use `std::time::Instant` or a user-supplied clock
   (for deterministic testing)?
3. `MultiManifold::snap` under `All` strategy returns all valid snaps — should it
   be capped to avoid allocation blowup on dense multi-surface configurations?

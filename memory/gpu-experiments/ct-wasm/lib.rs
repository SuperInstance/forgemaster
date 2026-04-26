mod holonomy;
mod snap;
mod triple;

use snap::{snap_brute, snap_by_angle};
use triple::{generate_triples, Triple};
use wasm_bindgen::prelude::*;

// ─── Panic hook (debug builds only) ────────────────────────────────────────

#[cfg(all(debug_assertions, target_arch = "wasm32"))]
#[wasm_bindgen(start)]
pub fn init_panic_hook() {
    std::panic::set_hook(Box::new(console_error_panic_hook));
}

#[cfg(all(debug_assertions, target_arch = "wasm32"))]
fn console_error_panic_hook(info: &std::panic::PanicInfo) {
    let msg = info.to_string();
    web_sys_log(&msg);
}

#[cfg(target_arch = "wasm32")]
#[wasm_bindgen]
extern "C" {
    #[wasm_bindgen(js_namespace = console, js_name = error)]
    fn web_sys_log(s: &str);
}

// ─── Manifold ───────────────────────────────────────────────────────────────

/// The snap manifold: a sorted collection of Pythagorean triple points on
/// the unit circle, with O(log n) nearest-neighbour queries.
#[wasm_bindgen]
pub struct Manifold {
    triples: Vec<Triple>,
}

#[wasm_bindgen]
impl Manifold {
    /// Build the manifold for all Pythagorean triples with hypotenuse ≤ max_c.
    /// This is the expensive step (~2–15 ms at max_c = 50 000); call it once
    /// on startup and again when the slider changes (debounced in JS).
    #[wasm_bindgen(constructor)]
    pub fn new(max_c: u32) -> Manifold {
        let triples = generate_triples(max_c.max(5));
        Manifold { triples }
    }

    /// Number of triple points on this manifold.
    pub fn len(&self) -> usize {
        self.triples.len()
    }

    /// True if the manifold has no points (should not happen for max_c ≥ 5).
    pub fn is_empty(&self) -> bool {
        self.triples.is_empty()
    }

    /// Snap (qx, qy) to the nearest triple point.  Returns the triple index.
    /// O(log n) binary search on the angle-sorted array.
    pub fn snap(&self, qx: f64, qy: f64) -> usize {
        snap_by_angle(qx, qy, &self.triples)
    }

    /// Return `[a, b, c]` for the triple at `idx` as a `Float64Array`.
    pub fn triple_at(&self, idx: usize) -> Vec<f64> {
        match self.triples.get(idx) {
            Some(t) => vec![t.a as f64, t.b as f64, t.c as f64],
            None => vec![0.0, 0.0, 0.0],
        }
    }

    /// Return `[x, y]` normalised coordinates for triple at `idx`.
    pub fn point_at(&self, idx: usize) -> Vec<f64> {
        match self.triples.get(idx) {
            Some(t) => {
                let (x, y) = t.normalized();
                vec![x, y]
            }
            None => vec![0.0, 0.0],
        }
    }

    /// Return all normalised points as a flat `[x0, y0, x1, y1, …]` array.
    /// Used by the canvas renderer to draw the full triple cloud at once.
    pub fn all_points(&self) -> Vec<f64> {
        self.triples
            .iter()
            .flat_map(|t| {
                let (x, y) = t.normalized();
                [x, y]
            })
            .collect()
    }

    /// Return all angles (radians) as a `Float64Array`.
    pub fn all_angles(&self) -> Vec<f64> {
        self.triples.iter().map(|t| t.angle()).collect()
    }

    /// Walk a closed angular path, snapping at every step.
    /// `angle_deltas` should sum to approximately zero for a closed path.
    /// Returns the Euclidean displacement between end and start positions.
    pub fn measure_holonomy(&self, angle_deltas: Vec<f64>) -> f64 {
        holonomy::measure_holonomy(&angle_deltas, &self.triples)
    }

    /// Run `n` angle-sorted (O(log n)) snaps with a fixed LCG seed.
    /// Returns `n` — the caller times the wall-clock duration to compute Mqps.
    pub fn bench_snap(&self, n: u32) -> u32 {
        let mut seed = 0xDEAD_BEEF_u64;
        for _ in 0..n {
            let qx = lcg_f64(&mut seed) * 2.0 - 1.0;
            let qy = lcg_f64(&mut seed) * 2.0 - 1.0;
            std::hint::black_box(snap_by_angle(qx, qy, &self.triples));
        }
        n
    }

    /// Run `n` brute-force O(n) snaps with the same LCG seed as `bench_snap`.
    /// Returns `n` — used for the performance comparison panel.
    pub fn bench_snap_brute(&self, n: u32) -> u32 {
        let mut seed = 0xDEAD_BEEF_u64;
        for _ in 0..n {
            let qx = lcg_f64(&mut seed) * 2.0 - 1.0;
            let qy = lcg_f64(&mut seed) * 2.0 - 1.0;
            std::hint::black_box(snap_brute(qx, qy, &self.triples));
        }
        n
    }
}

// ─── helpers ────────────────────────────────────────────────────────────────

/// Fast LCG pseudo-random number generator (Knuth MMIX constants).
/// Avoids a `rand` dependency and keeps the WASM binary small.
#[inline]
fn lcg_f64(seed: &mut u64) -> f64 {
    *seed = seed
        .wrapping_mul(6_364_136_223_846_793_005)
        .wrapping_add(1_442_695_040_888_963_407);
    ((*seed >> 33) as f64) / (u32::MAX as f64)
}

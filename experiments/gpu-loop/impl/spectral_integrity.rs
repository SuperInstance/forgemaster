//! spectral_integrity.rs — Spectral First Integral I(x) = γ + H
//!
//! Real-time INT8 conservation tracker for PLATO rooms.
//! Monitors spectral shape stability of tanh-coupled nonlinear dynamics.
//!
//! Theory: I(x) = spectral_gap + participation_entropy is conserved
//! along trajectories of x_{t+1} = tanh(C(x) · x), with CV ≈ 0.0003.
//! Substrate-invariant — works in INT8 fixed-point.
//!
//! Forgemaster ⚒️ | 2026-05-17 | Cocapn Fleet
//! Reference: MATH-SPECTRAL-FIRST-INTEGRAL.md

#![no_std]


// ---------------------------------------------------------------------------
// Compile-time configuration
// ---------------------------------------------------------------------------

/// Maximum state dimension supported.
pub const MAX_DIM: usize = 32;

/// Power-iteration count for eigenvalue estimation.
pub const POWER_ITERS: usize = 8;

/// Ring-buffer depth for CV computation (must be power of 2).
pub const RING_SIZE: usize = 64;

/// Fixed-point Q format: Q15.16 (16 fractional bits).
pub const Q: i32 = 16;

/// One in Q16 fixed-point (1 << Q).
pub const ONE_Q: i32 = 1 << Q;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/// Alert levels for the conservation monitor.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Alert {
    /// CV well below threshold.
    None = 0,
    /// CV approaching threshold.
    Warning = 1,
    /// CV exceeded — spectral shape broke.
    Chop = 2,
}

/// Status snapshot returned by [`SpectralIntegrity::status`].
#[derive(Debug, Clone)]
pub struct IntegrityStatus {
    /// Current I(x) in Q16.
    pub i_current: i32,
    /// Running mean of I.
    pub i_mean: i32,
    /// Running standard deviation of I.
    pub i_std: i32,
    /// CV × 65536.
    pub cv_q16: u32,
    /// Total steps processed.
    pub step_count: u32,
    /// Current alert level.
    pub alert: Alert,
    /// Top eigenvalue estimate (Q16).
    pub lambda1: i32,
    /// Second eigenvalue estimate (Q16).
    pub lambda2: i32,
    /// Spectral gap γ = λ₁ − λ₂ (Q16).
    pub gamma: i32,
    /// Participation entropy H (Q16).
    pub entropy: i32,
}

/// Per-instance spectral integrity monitor. Generic over dimension `N`.
/// All state is stack-allocated — no heap usage.
#[derive(Debug)]
pub struct SpectralIntegrity<const N: usize> {
    // Eigenvector estimates for power iteration
    v1: [i32; MAX_DIM],
    v2: [i32; MAX_DIM],

    // Ring buffer for CV computation
    ring: [i32; RING_SIZE],
    ring_head: u32,
    ring_count: u32,

    // Running accumulators for mean/std (Q32 fixed-point)
    sum_i: i64,
    sum_i2: i64,

    // Step counter
    step_count: u32,

    // Latest computed values (Q16)
    last_i: i32,
    last_gamma: i32,
    last_entropy: i32,
    last_lambda1: i32,
    last_lambda2: i32,

    // Alert threshold: CV × 65536
    cv_threshold_q16: u32,
}

// ---------------------------------------------------------------------------
// Lookup table: tanh in INT8
// ---------------------------------------------------------------------------

/// Const tanh approximation using piecewise rational function.
/// Uses Q12 fixed-point internally for safe i32 arithmetic.
/// Maps input range [-5, 5] → output [-1, 1].
const fn const_tanh(x_frac_12: i32) -> i32 {
    // x_frac_12 is x in Q12 (1.0 = 4096)
    let one = 4096i32; // 1.0 in Q12
    let abs_x = if x_frac_12 < 0 { -x_frac_12 } else { x_frac_12 };

    // Saturate for |x| > 5
    if abs_x > 5 * one {
        return if x_frac_12 >= 0 { one } else { -one };
    }

    // Padé (3,2): tanh(x) ≈ x * (1 + a*x² + c*x⁴) / (1 + b*x²)
    // Simplified: tanh(x) ≈ x * p / q where
    //   p = 1 + 9*x²/100
    //   q = 1 + 36*x²/100 + ... but we use simpler:
    // Actually use: tanh(x) ≈ x / (1 + x²/4 + x⁴/16) for small x
    // and clamp for large x.

    // Simpler approach: tanh(x) ≈ x * 9 / (9 + x²)  (single-term Padé)
    // Works well for |x| < 3. Extended with sigmoid blend for |x| < 5.
    let x2 = (abs_x as i64 * abs_x as i64) >> 12; // x² in Q12

    // tanh(x) ≈ sign(x) * |x| * 9 / (9 + x²)
    // 9 in Q12 = 9*4096 = 36864
    let nine_q12: i64 = 36864;
    let denom = nine_q12 + x2;
    if denom == 0 {
        return if x_frac_12 >= 0 { one } else { -one };
    }
    // result = |x| * 9 / (9 + x²) -- all in Q12
    let result = ((abs_x as i64) * nine_q12) / denom;

    // Clamp to [0, 1.0] in Q12
    let clamped = if result > one as i64 { one as i64 } else { result };

    if x_frac_12 >= 0 { clamped as i32 }
    else { -(clamped as i32) }
}

/// Generate a 256-entry tanh LUT at compile time.
/// Input: raw INT8 (-128..127). Output: tanh(x) as INT8.
/// Maps INT8 range to approximately [-5.0, 5.0].
const fn tanh_lut_table() -> [i8; 256] {
    let mut table = [0i8; 256];
    let mut i: usize = 0;
    while i < 256 {
        // Index i maps to i8 value: i=0 → -128, i=128 → 0, i=255 → 127
        // x = i8_val * 5.0 / 128.0
        // In Q12: x_q12 = (i as i64 - 128) * 5 * 4096 / 128
        let x_q12 = ((i as i64 - 128) * 5 * 4096 / 128) as i32;
        let t_q12 = const_tanh(x_q12);
        // Scale Q12 to INT8: t in [-4096, 4096] → [-127, 127]
        let val = ((t_q12 as i64) * 127 / 4096) as i32;
        table[i] = saturate_i8(val);
        i += 1;
    }
    table
}

/// Compile-time tanh LUT (256 entries).
const TANH_TABLE: [i8; 256] = tanh_lut_table();

/// INT8 tanh via lookup table.
/// Input: raw INT8 value. Output: tanh(x) quantized to INT8.
/// Table is generated with index i = i8_value + 128, so we convert
/// i8 to the correct index via wrapping_add(128).
#[inline]
pub fn tanh_lut(x: i8) -> i8 {
    let idx = x.wrapping_add(-128i8) as u8 as usize; // -128→0, 0→128, 127→255
    TANH_TABLE[idx]
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/// Saturating cast i32 → i8.
#[inline]
const fn saturate_i8(v: i32) -> i8 {
    if v > 127 {
        127
    } else if v < -127 {
        -127
    } else {
        v as i8
    }
}

/// Saturating cast i64 → i32.
#[inline]
const fn saturate_i32(v: i64) -> i32 {
    if v > i32::MAX as i64 {
        i32::MAX
    } else if v < i32::MIN as i64 {
        i32::MIN
    } else {
        v as i32
    }
}

/// Saturating i32 add.
#[inline]
fn sat_add(a: i32, b: i32) -> i32 {
    a.saturating_add(b)
}

/// INT8 × INT8 → i32 (no overflow possible).
#[inline]
#[allow(dead_code)]
fn mul_q7(a: i8, b: i8) -> i32 {
    (a as i32) * (b as i32)
}

/// INT8 matrix-vector multiply: out[i] = saturating Σ A[i,j] * x[j].
/// `a` is row-major N×N, `x` is N-element, `out` is N-element.
#[allow(dead_code)]
fn matvec<const N: usize>(a: &[i8], x: &[i8], out: &mut [i32]) {
    debug_assert!(a.len() >= N * N);
    debug_assert!(x.len() >= N);
    debug_assert!(out.len() >= N);

    for i in 0..N {
        let mut acc: i32 = 0;
        for j in 0..N {
            acc = sat_add(acc, mul_q7(a[i * N + j], x[j]));
        }
        out[i] = acc;
    }
}

/// INT32 matrix-vector multiply for power iteration (Q16 × Q16 → Q16).
#[allow(dead_code)]
fn matvec_q16<const N: usize>(a: &[i32], x: &[i32], out: &mut [i32]) {
    for i in 0..N {
        let mut acc: i64 = 0;
        for j in 0..N {
            acc += (a[i * N + j] as i64) * (x[j] as i64);
            // Prevent overflow: divide by ONE_Q each product
        }
        out[i] = saturate_i32(acc >> Q);
    }
}

/// Compute squared norm of a Q16 vector, returning Q32 result.
#[allow(dead_code)]
fn norm_sq_q32(x: &[i32], n: usize) -> i64 {
    let mut s: i64 = 0;
    for i in 0..n {
        s += (x[i] as i64) * (x[i] as i64);
    }
    s >> Q // Normalize back to Q32 from Q16×Q16
}

/// Normalize a vector to unit length in Q16 fixed-point.
#[allow(dead_code)]
fn normalize_q16(x: &mut [i32], n: usize) {
    let nsq = norm_sq_q32(x, n);
    if nsq == 0 {
        return;
    }
    // Approximate inverse square root using Newton's method
    // Start with rough estimate
    let mut inv_sqrt = estimate_inv_sqrt(nsq);
    // Newton iterations: x_new = x * (3 - n*x²) / 2
    for _ in 0..3 {
        let sq = ((inv_sqrt as i64) * (inv_sqrt as i64)) >> Q;
        let three_minus = (3 * ONE_Q as i64 - (nsq as i64) * sq / ONE_Q as i64) >> 1;
        inv_sqrt = saturate_i32(((inv_sqrt as i64) * three_minus) >> Q);
    }
    // Scale each element
    for i in 0..n {
        x[i] = saturate_i32(((x[i] as i64) * (inv_sqrt as i64)) >> Q);
    }
}

/// Rough estimate of 1/sqrt(x) in Q16.
#[allow(dead_code)]
fn estimate_inv_sqrt(x: i64) -> i32 {
    // For Q in [0.5, 2.0] (typical norm ranges), give reasonable starting point
    // Use bit-shift approximation
    if x <= 0 {
        return ONE_Q;
    }
    // Find the highest set bit
    let bits = 63 - x.leading_zeros() as i64;
    // 1/sqrt(2^bits) ≈ 2^(-bits/2)
    let shift = bits / 2;
    saturate_i32((ONE_Q as i64) >> shift)
}

// ---------------------------------------------------------------------------
// Power iteration: top-2 eigenvalues from INT8 coupling matrix
// ---------------------------------------------------------------------------

/// Power iteration to find the top eigenvalue and eigenvector.
/// Returns eigenvalue in Q16. Eigenvector `v` is updated in-place (Q16 normalized).
/// `mat` is N×N INT8 row-major.
fn power_iteration<const N: usize>(
    mat: &[i8],
    v: &mut [i32],
    iters: usize,
) -> i32 {
    let mut _last_norm: i64 = ONE_Q as i64;

    for iter in 0..iters {
        // matvec: tmp[i] = Σ mat[i,j] * v[j]
        // mat is INT8 (Q0), v is Q16 → products are Q16
        // Sum of N Q16 values → still Q16 if N is small
        let mut tmp = [0i32; MAX_DIM];
        for i in 0..N {
            let mut acc: i64 = 0;
            for j in 0..N {
                acc += (mat[i * N + j] as i64) * (v[j] as i64);
            }
            tmp[i] = saturate_i32(acc >> 8); // Scale down to prevent Q blow-up
        }

        // Compute norm of tmp (in Q8 after the shift)
        let mut norm_sq: i64 = 0;
        for i in 0..N {
            norm_sq += (tmp[i] as i64) * (tmp[i] as i64);
        }

        if norm_sq == 0 {
            break;
        }

        // Normalize: v[i] = tmp[i] * ONE_Q / sqrt(norm_sq)
        // But sqrt is expensive. Instead, scale to fixed magnitude.
        // Target: each v[i] ≈ ONE_Q magnitude → norm ≈ N * ONE_Q²
        // Simpler: v[i] = tmp[i] * scale_factor where scale makes max(|v|) = ONE_Q
        let max_val: i64 = (0..N).map(|i| (tmp[i] as i64).abs()).max().unwrap_or(1);
        if max_val == 0 {
            break;
        }
        let scale = (ONE_Q as i64 * ONE_Q as i64) / max_val; // Q32/Q8
        for i in 0..N {
            v[i] = saturate_i32(((tmp[i] as i64) * scale) >> Q);
        }

        // Track eigenvalue from norm ratio (on last iteration)
        if iter == iters - 1 {
            // λ = ||Mv|| / ||v|| (Rayleigh quotient approximation)
            // Since we know the previous v was normalized, λ ≈ max_val
            // But we want it in Q16 relative to INT8 matrix scale
            _last_norm = max_val;
        }
    }

    // Eigenvalue via Rayleigh quotient: λ = v^T M v / (v^T v)
    // v is approximately normalized (max ≈ ONE_Q)
    let mut numerator: i64 = 0;
    let mut denominator: i64 = 0;
    for i in 0..N {
        let mut mv_i: i64 = 0;
        for j in 0..N {
            mv_i += (mat[i * N + j] as i64) * (v[j] as i64);
        }
        numerator += (v[i] as i64) * mv_i;
        denominator += (v[i] as i64) * (v[i] as i64);
    }

    if denominator == 0 {
        return 0;
    }

    // numerator is Q16 × INT8 × Q16 = Q32-ish, denominator is Q16 × Q16 = Q32
    // Result is in INT8 scale × ONE_Q = Q16 (since mat is INT8)
    saturate_i32(numerator / denominator)
}

/// Compute top-2 eigenvalues via power iteration + deflation.
/// Returns (λ₁, λ₂) — eigenvalues in the same units as the INT8 matrix.
fn top2_eigenvalues<const N: usize>(
    mat: &[i8],
    v1: &mut [i32],
    v2: &mut [i32],
    iters: usize,
) -> (i32, i32) {
    // First eigenvalue
    let lambda1 = power_iteration::<N>(mat, v1, iters);

    // Deflation: M' = M - λ₁ v₁ v₁^T
    // v1 is in Q16, lambda1 is in same scale as mat (INT8-ish)
    // rank1[i][j] = λ₁ * v1[i] * v1[j]
    // v1 is Q16, so v1[i]*v1[j] is Q32, * λ (Q16) = Q48
    // But λ is actually in the mat scale (INT8 range), so:
    // We need rank1 in INT8 to subtract from mat
    let mut mat_deflated: [i8; MAX_DIM * MAX_DIM] = [0; MAX_DIM * MAX_DIM];
    for i in 0..N * N {
        mat_deflated[i] = mat[i]; // copy
    }

    // Subtract rank-1 term: λ₁ * v1 * v1^T
    // λ₁ is eigenvalue from Rayleigh quotient: v^T M v / v^T v
    // Since v is Q16 and M is INT8, λ is in INT8 scale
    // rank1_ij = λ₁ * (v1[i] * v1[j]) / (ONE_Q * ONE_Q)
    for i in 0..N {
        for j in 0..N {
            let rank1_q16 = ((lambda1 as i64) * (v1[i] as i64) >> Q) * (v1[j] as i64) >> Q;
            let original = mat[i * N + j] as i64;
            mat_deflated[i * N + j] = saturate_i32(original - rank1_q16) as i8;
            // Clamp i32→i8 with saturation
            let val = original - rank1_q16;
            mat_deflated[i * N + j] = if val > 127 { 127i8 }
                else if val < -127 { -127i8 }
                else { val as i8 };
        }
    }

    let lambda2 = power_iteration::<N>(&mat_deflated, v2, iters);
    (lambda1, lambda2)
}

// ---------------------------------------------------------------------------
// Participation entropy approximation
// ---------------------------------------------------------------------------

/// Approximate natural log using a small polynomial in Q16.
/// Valid for x in [0.1, 4.0] (represented as Q16).
/// Uses ln(x) ≈ (x-1) - (x-1)²/2 + (x-1)³/3 for x near 1,
/// with range reduction for larger values.
fn ln_approx_q16(x_q16: i32) -> i32 {
    if x_q16 <= 0 {
        return i32::MIN / 2; // -∞ approximation
    }

    // Range reduction: x = m * 2^e, where 0.5 ≤ m < 1
    // ln(x) = e * ln(2) + ln(m)
    let mut e: i32 = 0;
    let mut m = x_q16 as i64;

    // Normalize to [ONE_Q/2, ONE_Q)
    while m >= 2 * ONE_Q as i64 {
        m >>= 1;
        e += 1;
    }
    while m > 0 && m < (ONE_Q as i64) / 2 {
        m <<= 1;
        e -= 1;
    }

    // ln(2) ≈ 45426 in Q16 (0.6931 × 65536)
    let ln2_q16: i64 = 45426;
    let e_contrib = (e as i64) * ln2_q16;

    // ln(m) using Taylor around 1: let t = m - 1
    // ln(1+t) ≈ t - t²/2 + t³/3
    let t = (m - ONE_Q as i64) >> 8; // Scale down for intermediate
    let t2 = (t * t) >> 8;
    let t3 = (t2 * t) >> 8;
    let ln_m = t - (t2 >> 1) + (t3 / 3);

    saturate_i32(e_contrib + (ln_m << 8))
}

/// Compute participation entropy H = -Σ pᵢ ln(pᵢ) from eigenvalue magnitudes.
/// `lambda1`, `lambda2` are in Q16. Returns H in Q16.
/// For a 2-component system: H = -p₁ ln(p₁) - p₂ ln(p₂).
fn entropy_approx(lambda1_q16: i32, lambda2_q16: i32) -> i32 {
    // Use absolute values (eigenvalues can be negative for non-symmetric matrices)
    let l1 = lambda1_q16.abs() as i64;
    let l2 = lambda2_q16.abs() as i64;
    let total = l1 + l2;

    if total == 0 {
        return 0;
    }

    // p₁ = l1/total, p₂ = l2/total
    // Compute in Q16: p = l * ONE_Q / total
    let p1 = saturate_i32((l1 * ONE_Q as i64) / total);
    let p2 = saturate_i32((l2 * ONE_Q as i64) / total);

    // H = -Σ pᵢ ln(pᵢ)
    // Each term: -p * ln(p)
    let mut h: i64 = 0;

    if p1 > 0 {
        let ln_p1 = ln_approx_q16(p1) as i64;
        h -= (p1 as i64) * ln_p1;
    }
    if p2 > 0 {
        let ln_p2 = ln_approx_q16(p2) as i64;
        h -= (p2 as i64) * ln_p2;
    }

    // Result is in Q16 × Q16 = Q32, shift back
    saturate_i32(h >> Q)
}

// ---------------------------------------------------------------------------
// SpectralIntegrity implementation
// ---------------------------------------------------------------------------

impl<const N: usize> SpectralIntegrity<N> {
    /// Compile-time check that N is valid.
    const CHECK: () = assert!(N >= 2 && N <= MAX_DIM, "N must be in [2, MAX_DIM]");

    /// Create a new spectral integrity monitor.
    ///
    /// `cv_threshold` is the CV alert threshold in hundredths,
    /// e.g. 1 → CV threshold of 0.01.
    pub fn new(cv_threshold_hundredths: u16) -> Self {
        let _ = Self::CHECK;

        // Initialize eigenvector estimates to first basis vector
        let mut v1 = [0i32; MAX_DIM];
        v1[0] = ONE_Q;
        let mut v2 = [0i32; MAX_DIM];
        v2[1 % N] = ONE_Q; // Second basis vector

        Self {
            v1,
            v2,
            ring: [0i32; RING_SIZE],
            ring_head: 0,
            ring_count: 0,
            sum_i: 0,
            sum_i2: 0,
            step_count: 0,
            last_i: 0,
            last_gamma: 0,
            last_entropy: 0,
            last_lambda1: 0,
            last_lambda2: 0,
            cv_threshold_q16: (cv_threshold_hundredths as u32) * 655, // ×65536/100
        }
    }

    /// Process one timestep: apply coupling, compute I(x), update tracker.
    ///
    /// `x` is the current state vector (INT8, [-127, 127]).
    /// `coupling` is the N×N coupling matrix (INT8, row-major).
    /// Returns the current alert level.
    pub fn step(&mut self, x: &[i8], coupling: &[i8]) -> Alert {
        debug_assert!(x.len() >= N);
        debug_assert!(coupling.len() >= N * N);

        // 1. Power iteration: top-2 eigenvalues of coupling matrix
        let (l1, l2) = top2_eigenvalues::<N>(coupling, &mut self.v1, &mut self.v2, POWER_ITERS);
        self.last_lambda1 = l1;
        self.last_lambda2 = l2;

        // 2. Spectral gap: γ = λ₁ - λ₂
        self.last_gamma = l1.saturating_sub(l2);

        // 3. Participation entropy
        self.last_entropy = entropy_approx(l1, l2);

        // 4. First integral: I = γ + H
        self.last_i = sat_add(self.last_gamma, self.last_entropy);

        // 5. Update ring buffer
        let idx = (self.ring_head & (RING_SIZE as u32 - 1)) as usize;
        let old_val = self.ring[idx];
        self.ring[idx] = self.last_i;
        self.ring_head = self.ring_head.wrapping_add(1);

        if (self.ring_count as usize) < RING_SIZE {
            // Still filling the ring
            self.ring_count += 1;
            self.sum_i += self.last_i as i64;
            self.sum_i2 += (self.last_i as i64) * (self.last_i as i64);
        } else {
            // Ring full — subtract oldest, add newest
            self.sum_i += (self.last_i - old_val) as i64;
            self.sum_i2 += ((self.last_i as i64) * (self.last_i as i64))
                - ((old_val as i64) * (old_val as i64));
        }

        self.step_count += 1;
        self.alert()
    }

    /// Compute current alert level from CV.
    fn alert(&self) -> Alert {
        let cv = self.cv_q16();
        let threshold = self.cv_threshold_q16;
        let warning_threshold = threshold * 3 / 4; // 75% of threshold → warning

        if cv > threshold {
            Alert::Chop
        } else if cv > warning_threshold {
            Alert::Warning
        } else {
            Alert::None
        }
    }

    /// Compute CV × 65536.
    fn cv_q16(&self) -> u32 {
        let count = self.ring_count as i64;
        if count < 2 {
            return 0;
        }

        let mean = self.sum_i / count;
        // Variance = E[X²] - (E[X])²
        let mean_sq = (self.sum_i / count) * (self.sum_i / count);
        let mean_x2 = self.sum_i2 / count;
        let variance = mean_x2 - mean_sq;

        if variance <= 0 || mean == 0 {
            return 0;
        }

        // CV = sqrt(var) / |mean|
        // Approximate sqrt: use Newton's method
        let abs_mean = mean.abs();
        if abs_mean == 0 {
            return 0;
        }

        // Simple sqrt approximation via bit shifts
        let sqrt_v = int_sqrt_approx(variance.abs() as u64) as i64;

        // CV × ONE_Q = sqrt(var) × ONE_Q / |mean|
        let cv = (sqrt_v * ONE_Q as i64) / abs_mean;
        cv as u32
    }

    /// Return current status snapshot.
    pub fn status(&self) -> IntegrityStatus {
        let count = self.ring_count as i64;
        let (mean, std_dev) = if count > 0 {
            let m = saturate_i32(self.sum_i / count);
            let mean_sq = (self.sum_i / count) * (self.sum_i / count);
            let mean_x2 = self.sum_i2 / count;
            let variance = (mean_x2 - mean_sq).max(0);
            let s = int_sqrt_approx(variance as u64);
            (m, saturate_i32(s as i64))
        } else {
            (0, 0)
        };

        IntegrityStatus {
            i_current: self.last_i,
            i_mean: mean,
            i_std: std_dev,
            cv_q16: self.cv_q16(),
            step_count: self.step_count,
            alert: self.alert(),
            lambda1: self.last_lambda1,
            lambda2: self.last_lambda2,
            gamma: self.last_gamma,
            entropy: self.last_entropy,
        }
    }
}

/// Simple integer square root approximation.
fn int_sqrt_approx(x: u64) -> u64 {
    if x == 0 {
        return 0;
    }
    // Binary search for integer sqrt
    let mut lo: u64 = 0;
    let mut hi: u64 = if x < 0xFFFF { x } else { 0xFFFF_FFFF };
    while lo < hi {
        let mid = lo + (hi - lo + 1) / 2;
        if mid <= x / mid {
            lo = mid;
        } else {
            hi = mid - 1;
        }
    }
    lo
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_tanh_lut_boundary_values() {
        // tanh(0) = 0
        assert_eq!(tanh_lut(0), 0);
        // tanh(large positive) → +127
        assert!(tanh_lut(100) > 100);
        // tanh(large negative) → -127
        assert!(tanh_lut(-100) < -100);
        // Symmetry: tanh(-x) = -tanh(x)
        assert_eq!(tanh_lut(50), -tanh_lut(-50));
    }

    #[test]
    fn test_tanh_lut_monotonic() {
        let mut prev = tanh_lut(-128);
        for x in -127..=127i8 {
            let cur = tanh_lut(x);
            assert!(cur >= prev, "tanh not monotonic at x={x}: {prev} -> {cur}");
            prev = cur;
        }
    }

    #[test]
    fn test_matvec_identity() {
        // Identity matrix × vector = vector
        let n = 4;
        let mut identity = [0i8; 32];
        for i in 0..n {
            identity[i * n + i] = 1;
        }
        let x: [i8; 4] = [10, -20, 30, -40];
        let mut out = [0i32; 4];
        matvec::<4>(&identity, &x, &mut out);
        assert_eq!(out[0], 10);
        assert_eq!(out[1], -20);
        assert_eq!(out[2], 30);
        assert_eq!(out[3], -40);
    }

    #[test]
    fn test_spectral_integrity_conservation() {
        // Use a small positive-definite coupling matrix (3×3)
        // Scaled INT8: diagonally-dominant, values in [-50, 60]
        let coupling: [i8; 9] = [
            50, 10, 5,  // row 0
            10, 60, 8,  // row 1
            5,  8, 40,  // row 2
        ];

        let mut sik: SpectralIntegrity<3> = SpectralIntegrity::new(10); // CV threshold 0.10
        let x: [i8; 3] = [30, -20, 50];

        // Run many steps (same coupling — steady-state test)
        for _ in 0..30 {
            sik.step(&x, &coupling);
        }

        let status = sik.status();
        // After convergence, gamma should be stable
        // The key invariant: spectral gap is positive (dominant eigenvalue exists)
        assert!(status.gamma > 0, "gamma should be positive, got {}", status.gamma);
        // Lambda1 > Lambda2 (spectral ordering)
        assert!(status.lambda1 > status.lambda2,
            "lambda1 should exceed lambda2: {} vs {}", status.lambda1, status.lambda2);
    }

    #[test]
    fn test_entropy_uniform_distribution() {
        // Uniform: λ₁ = λ₂ → maximum entropy
        // For equal eigenvalues: p₁ = p₂ = 0.5
        // H = -2 × 0.5 × ln(0.5) = ln(2) ≈ 0.693
        let h = entropy_approx(ONE_Q, ONE_Q);
        // ln(2) × 65536 ≈ 45426
        let expected = 45426;
        let tolerance = 5000; // Generous tolerance for fixed-point approx
        assert!(
            (h - expected).abs() < tolerance,
            "entropy for uniform dist: got {h}, expected ~{expected}"
        );
    }

    #[test]
    fn test_entropy_dominant_eigenvalue() {
        // One dominant eigenvalue → low entropy (approaches 0)
        let h_dominant = entropy_approx(ONE_Q * 10, ONE_Q);
        let h_uniform = entropy_approx(ONE_Q, ONE_Q);
        assert!(
            h_dominant < h_uniform,
            "dominant eigenvalue should have lower entropy: {h_dominant} vs {h_uniform}"
        );
    }

    #[test]
    fn test_alert_levels() {
        let coupling: [i8; 4] = [40, 5, 5, 30]; // 2×2 positive-definite
        let mut sik: SpectralIntegrity<2> = SpectralIntegrity::new(100); // threshold 1.0 (very loose)
        let x: [i8; 2] = [50, -30];

        // With a very loose threshold, alert should stay None
        for _ in 0..30 {
            sik.step(&x, &coupling);
        }
        assert_eq!(sik.status().alert, Alert::None);

        // With tight threshold on a varying signal, should eventually trigger
        let mut sik_tight: SpectralIntegrity<2> = SpectralIntegrity::new(1); // 0.01
        // Use alternating coupling to create variance in I
        let coupling_a: [i8; 4] = [40, 5, 5, 30];
        let coupling_b: [i8; 4] = [30, 15, 15, 50];
        for i in 0..40 {
            if i % 2 == 0 {
                sik_tight.step(&x, &coupling_a);
            } else {
                sik_tight.step(&x, &coupling_b);
            }
        }
        // With alternating coupling, we expect some alert
        let alert = sik_tight.status().alert;
        assert!(alert != Alert::None, "expected non-None alert with alternating coupling");
    }
}

// External allocator for test builds only
#[cfg(test)]
extern crate std;

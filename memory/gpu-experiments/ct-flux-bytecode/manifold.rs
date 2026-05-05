//! Pythagorean manifold for FLUX constraint theory.
//!
//! The manifold consists of Pythagorean triples (a, b, c) where a² + b² = c².
//! Snapping projects a scalar flux value onto this discrete constraint surface,
//! enforcing the hard geometric constraint at runtime.

/// Generate a Pythagorean triple using Euclid's formula with m = n + 1.
///
/// For any positive `n`, the returned triple satisfies:
/// a = m² − n² = 2n + 1  
/// b = 2mn = 2n² + 2n    
/// c = m² + n² = 2n² + 2n + 1
///
/// # Constraint theory interpretation
/// This is a **parametric generator** for the constraint surface.  Every
/// valid triple is a point where the Pythagorean identity (the hard
/// constraint) is exactly satisfied.
pub fn generate_triples(n: f64) -> (f64, f64, f64) {
    let m = n + 1.0;
    let a = m * m - n * n;
    let b = 2.0 * m * n;
    let c = m * m + n * n;
    (a, b, c)
}

/// Snap a scalar flux value to the Pythagorean manifold.
///
/// The input is floored and clamped to a positive base, then mapped through
/// Euclid's formula.  The result is the nearest discrete triple on the
/// constraint surface.
///
/// # Constraint theory interpretation
/// **Snapping** is the core operation of constraint theory: an unconstrained
/// (continuous) value is projected onto the discrete manifold, yielding a
/// configuration that satisfies all geometric laws exactly.
pub fn snap(x: f64) -> (f64, f64, f64) {
    let n = x.abs().floor().max(1.0);
    generate_triples(n)
}

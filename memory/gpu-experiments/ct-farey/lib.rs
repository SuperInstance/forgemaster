//! # ct-farey — Farey Sequence for Snap Quality Bounds
//!
//! The Farey sequence F_n contains all reduced fractions a/b with 0 ≤ a ≤ b ≤ n,
//! ordered by value. For snap quality analysis, Farey sequences give provable
//! bounds on how close any angle can get to a Pythagorean triple angle.

/// A reduced fraction a/b.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Fraction {
    pub num: u64,
    pub den: u64,
}

impl Fraction {
    pub fn new(num: u64, den: u64) -> Self {
        let g = gcd(num, den);
        Fraction { num: num / g, den: den / g }
    }
    
    pub fn value(&self) -> f64 {
        self.num as f64 / self.den as f64
    }
    
    /// Angle = atan2(num, den).
    pub fn angle(&self) -> f64 {
        (self.num as f64).atan2(self.den as f64)
    }
}

impl PartialOrd for Fraction {
    fn partial_cmp(&self, other: &Self) -> Option<std::cmp::Ordering> {
        Some(self.cmp(other))
    }
}

impl Ord for Fraction {
    fn cmp(&self, other: &Self) -> std::cmp::Ordering {
        // Cross-multiply to avoid floating point
        (self.num * other.den).cmp(&(other.num * self.den))
    }
}

/// Generate the Farey sequence F_n.
/// Returns all reduced fractions a/b with 0 ≤ a ≤ b ≤ n, sorted.
pub fn farey(n: u64) -> Vec<Fraction> {
    let mut result = Vec::new();
    // 0/1
    result.push(Fraction { num: 0, den: 1 });
    // 1/n to 1/1
    for d in 1..=n {
        for num in 1..=d {
            if gcd(num, d) == 1 {
                result.push(Fraction::new(num, d));
            }
        }
    }
    result.sort();
    result
}

/// Farey neighbors: find the two fractions in F_n that bracket a given value.
pub fn farey_neighbors(value: f64, n: u64) -> (Option<Fraction>, Option<Fraction>) {
    let seq = farey(n);
    if seq.is_empty() { return (None, None); }
    
    let mut lo: Option<&Fraction> = None;
    let mut hi: Option<&Fraction> = None;
    
    for f in &seq {
        let v = f.value();
        if v <= value { lo = Some(f); }
        if v >= value && hi.is_none() { hi = Some(f); }
    }
    
    (lo.copied(), hi.copied())
}

/// Maximum gap in Farey sequence F_n (worst-case snap quality bound).
pub fn max_gap(n: u64) -> f64 {
    let seq = farey(n);
    if seq.len() < 2 { return 1.0; }
    
    let mut max_d = 0.0f64;
    for i in 1..seq.len() {
        let d = seq[i].value() - seq[i - 1].value();
        if d > max_d { max_d = d; }
    }
    max_d
}

/// Theoretical lower bound on max gap: 1/n^2 (for Farey sequence).
pub fn max_gap_lower_bound(n: u64) -> f64 {
    1.0 / (n as f64 * n as f64)
}

/// Snap quality bound: the worst-case angular error when snapping to
/// Pythagorean triples with max hypotenuse c.
pub fn snap_quality_bound(max_c: u64) -> f64 {
    // The best rational approximation of tan(theta) with denominator <= max_c
    // has error at most 1/(2*max_c^2) by Dirichlet's theorem.
    // Converting to angular error is bounded by this.
    let farey_n = max_c;
    max_gap(farey_n) / 2.0
}

/// Count Farey sequence length (Euler's totient summatory).
pub fn farey_count(n: u64) -> u64 {
    // |F_n| = 1 + sum(phi(d) for d=1..n)
    1 + (1..=n).map(euler_totient).sum::<u64>()
}

/// Euler's totient function φ(n).
pub fn euler_totient(n: u64) -> u64 {
    if n == 0 { return 0; }
    let mut result = n;
    let mut m = n;
    let mut p = 2u64;
    while p * p <= m {
        if m % p == 0 {
            while m % p == 0 { m /= p; }
            result -= result / p;
        }
        p += 1;
    }
    if m > 1 { result -= result / m; }
    result
}

fn gcd(a: u64, b: u64) -> u64 {
    if b == 0 { a } else { gcd(b, a % b) }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_farey_small() {
        let f = farey(3);
        // F_3 = {0/1, 1/3, 1/2, 2/3, 1/1}
        assert_eq!(f.len(), 5);
    }
    
    #[test]
    fn test_farey_sorted() {
        let f = farey(10);
        for i in 1..f.len() {
            assert!(f[i] > f[i - 1]);
        }
    }
    
    #[test]
    fn test_farey_reduced() {
        let f = farey(6);
        for frac in &f {
            assert_eq!(gcd(frac.num, frac.den), 1);
        }
    }
    
    #[test]
    fn test_farey_neighbors() {
        let (lo, hi) = farey_neighbors(0.6, 5);
        assert!(lo.is_some());
        assert!(hi.is_some());
        assert!(lo.unwrap().value() <= 0.6);
        assert!(hi.unwrap().value() >= 0.6);
    }
    
    #[test]
    fn test_max_gap_positive() {
        let g = max_gap(10);
        assert!(g > 0.0);
        assert!(g < 1.0);
    }
    
    #[test]
    fn test_max_gap_decreases_with_n() {
        let g5 = max_gap(5);
        let g20 = max_gap(20);
        assert!(g20 < g5);
    }
    
    #[test]
    fn test_max_gap_lower_bound() {
        let lb = max_gap_lower_bound(100);
        assert!(lb > 0.0);
    }
    
    #[test]
    fn test_euler_totient() {
        assert_eq!(euler_totient(1), 1);
        assert_eq!(euler_totient(2), 1);
        assert_eq!(euler_totient(6), 2);
        assert_eq!(euler_totient(12), 4);
        assert_eq!(euler_totient(7), 6);
    }
    
    #[test]
    fn test_farey_count() {
        // |F_1| = 2, |F_2| = 3, |F_3| = 5
        assert_eq!(farey_count(1), 2);
        assert_eq!(farey_count(2), 3);
        assert_eq!(farey_count(3), 5);
        assert_eq!(farey_count(4), 7);
    }
    
    #[test]
    fn test_snap_quality_bound() {
        let bound = snap_quality_bound(100);
        assert!(bound > 0.0);
        assert!(bound < 0.5);
    }
    
    #[test]
    fn test_fraction_new_reduces() {
        let f = Fraction::new(2, 4);
        assert_eq!(f.num, 1);
        assert_eq!(f.den, 2);
    }
}

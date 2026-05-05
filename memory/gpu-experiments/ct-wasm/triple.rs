/// A Pythagorean triple (a, b, c) with a² + b² = c².
/// Points are normalised to the unit circle: (a/c, b/c).
#[derive(Clone, Debug)]
pub struct Triple {
    pub a: u32,
    pub b: u32,
    pub c: u32,
}

impl Triple {
    /// Angle of the normalised point on the unit circle, in (-π, π].
    #[inline]
    pub fn angle(&self) -> f64 {
        (self.b as f64).atan2(self.a as f64)
    }

    /// Normalised Cartesian coordinates (a/c, b/c).
    #[inline]
    pub fn normalized(&self) -> (f64, f64) {
        let c = self.c as f64;
        (self.a as f64 / c, self.b as f64 / c)
    }
}

/// Euclid's GCD via iterative subtraction (Stein-style division variant).
pub fn gcd(mut a: u32, mut b: u32) -> u32 {
    while b != 0 {
        let t = b;
        b = a % b;
        a = t;
    }
    a
}

/// Generate all Pythagorean triples with hypotenuse ≤ max_c, returned
/// sorted by angle (atan2(b, a)).  Both (a, b, c) and (b, a, c) are
/// included when a ≠ b, giving full first-quadrant coverage.
///
/// Uses Euclid's parametric formula:
///   a = k(m² - n²),  b = k(2mn),  c = k(m² + n²)
///   with m > n > 0,  gcd(m,n) = 1,  m - n odd.
pub fn generate_triples(max_c: u32) -> Vec<Triple> {
    let mut triples = Vec::new();

    // m² + n² ≤ max_c  and  n ≥ 1  ⟹  m ≤ √(max_c - 1)
    let m_max = (max_c as f64).sqrt() as u32 + 1;

    for m in 2..=m_max {
        for n in 1..m {
            // m and n must have opposite parity (m - n odd ↔ m + n odd)
            if (m + n) % 2 == 0 {
                continue;
            }
            if gcd(m, n) != 1 {
                continue;
            }

            let a0 = m * m - n * n;
            let b0 = 2 * m * n;
            let c0 = m * m + n * n;

            if c0 > max_c {
                continue;
            }

            // Emit all non-primitive multiples k·(a₀, b₀, c₀)
            let mut k = 1u32;
            loop {
                let c = match c0.checked_mul(k) {
                    Some(v) if v <= max_c => v,
                    _ => break,
                };
                let a = a0 * k;
                let b = b0 * k;

                triples.push(Triple { a, b, c });
                if a != b {
                    // Symmetric triple: swap legs → different point on circle
                    triples.push(Triple { a: b, b: a, c });
                }
                k += 1;
            }
        }
    }

    // Sort by angle so the snap binary-search works correctly
    triples.sort_by(|p, q| p.angle().partial_cmp(&q.angle()).unwrap_or(std::cmp::Ordering::Equal));
    triples
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn gcd_basics() {
        assert_eq!(gcd(12, 8), 4);
        assert_eq!(gcd(5, 0), 5);
        assert_eq!(gcd(0, 7), 7);
        assert_eq!(gcd(1, 1), 1);
    }

    #[test]
    fn smallest_triple_345() {
        let ts = generate_triples(5);
        // (3,4,5) and (4,3,5) must both appear
        assert!(ts.iter().any(|t| t.a == 3 && t.b == 4 && t.c == 5));
        assert!(ts.iter().any(|t| t.a == 4 && t.b == 3 && t.c == 5));
    }

    #[test]
    fn sorted_by_angle() {
        let ts = generate_triples(100);
        for w in ts.windows(2) {
            assert!(w[0].angle() <= w[1].angle());
        }
    }

    #[test]
    fn pythagorean_identity() {
        for t in generate_triples(200) {
            assert_eq!(t.a * t.a + t.b * t.b, t.c * t.c, "{:?}", t);
        }
    }
}

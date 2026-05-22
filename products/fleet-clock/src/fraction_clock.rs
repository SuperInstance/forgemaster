//! Zero-drift Fraction clock using exact rational arithmetic.

use core::cmp::Ordering;

/// Exact rational number with no floating-point drift.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct Fraction {
    /// Numerator (signed)
    pub num: i64,
    /// Denominator (always positive, never zero)
    pub den: u64,
}

impl Fraction {
    /// Create a new fraction. Panics if `den == 0`.
    pub fn new(num: i64, den: u64) -> Self {
        assert!(den != 0, "denominator must be non-zero");
        let f = Fraction { num, den };
        f.reduced()
    }

    /// Zero: 0/1
    pub const ZERO: Fraction = Fraction { num: 0, den: 1 };

    /// One: 1/1
    pub const ONE: Fraction = Fraction { num: 1, den: 1 };

    /// Create from an integer.
    pub fn from_int(n: i64) -> Self {
        Fraction { num: n, den: 1 }
    }

    /// Convert to f64 (lossy).
    pub fn to_f64(self) -> f64 {
        self.num as f64 / self.den as f64
    }

    /// Reduce to lowest terms.
    fn reduced(mut self) -> Self {
        if self.num == 0 {
            self.den = 1;
            return self;
        }
        let g = gcd(self.num.unsigned_abs(), self.den);
        self.num /= g as i64;
        self.den /= g;
        // Keep denominator positive
        if self.num < 0 && self.den > 0 {
            // already fine
        } else if self.num >= 0 && self.den > 0 {
            // fine
        }
        self
    }

    /// Add two fractions.
    pub fn add(self, other: Fraction) -> Fraction {
        Fraction::new(
            self.num * other.den as i64 + other.num * self.den as i64,
            self.den * other.den,
        )
    }

    /// Subtract.
    pub fn sub(self, other: Fraction) -> Fraction {
        self.add(Fraction {
            num: -other.num,
            den: other.den,
        })
    }

    /// Multiply.
    pub fn mul(self, other: Fraction) -> Fraction {
        Fraction::new(self.num * other.num, self.den * other.den)
    }

    /// Absolute value.
    pub fn abs(self) -> Fraction {
        Fraction {
            num: self.num.unsigned_abs() as i64,
            den: self.den,
        }
    }

    /// Round to nearest integer.
    pub fn round(self) -> i64 {
        let half = Fraction::new(1, 2);
        if self.num >= 0 {
            (self.add(half)).num / (self.add(half)).den as i64
        } else {
            -((-self).add(half).num as i64 / (-self).add(half).den as i64)
        }
    }
}

fn gcd(a: u64, b: u64) -> u64 {
    let mut a = a;
    let mut b = b;
    while b != 0 {
        let t = b;
        b = a % b;
        a = t;
    }
    a
}

impl PartialOrd for Fraction {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl Ord for Fraction {
    fn cmp(&self, other: &Self) -> Ordering {
        // a/b vs c/d => a*d vs c*b
        let lhs = self.num as i128 * other.den as i128;
        let rhs = other.num as i128 * self.den as i128;
        lhs.cmp(&rhs)
    }
}

impl Default for Fraction {
    fn default() -> Self {
        Fraction::ZERO
    }
}

#[cfg(feature = "serde")]
mod serde_impl {
    use super::Fraction;
    use serde::{Deserialize, Deserializer, Serialize, Serializer};

    impl Serialize for Fraction {
        fn serialize<S: Serializer>(&self, s: S) -> Result<S::Ok, S::Error> {
            (&self.num, &self.den).serialize(s)
        }
    }

    impl<'de> Deserialize<'de> for Fraction {
        fn deserialize<D: Deserializer<'de>>(d: D) -> Result<Self, D::Error> {
            let (num, den): (i64, u64) = Deserialize::deserialize(d)?;
            Ok(Fraction::new(num, den))
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_new_reduces() {
        let f = Fraction::new(4, 8);
        assert_eq!(f.num, 1);
        assert_eq!(f.den, 2);
    }

    #[test]
    fn test_add() {
        let a = Fraction::new(1, 3);
        let b = Fraction::new(1, 6);
        let c = a.add(b);
        assert_eq!(c, Fraction::new(1, 2));
    }

    #[test]
    fn test_ordering() {
        assert!(Fraction::new(1, 3) < Fraction::new(1, 2));
        assert!(Fraction::new(2, 3) > Fraction::new(1, 2));
    }
}

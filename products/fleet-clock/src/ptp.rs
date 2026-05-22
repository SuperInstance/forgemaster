//! PTP-style offset estimation for distributed clock sync.
//!
//! Uses libm for f64 operations to support no_std targets.

use crate::fraction_clock::Fraction;

/// PTP synchronization mode.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PtpMode {
    /// Estimate offset using (t1, t2, t3, t4) four-timestamp method.
    OffsetEstimation,
    /// No PTP correction — free-running.
    FreeRunning,
}

/// A single PTP exchange record between two agents.
#[derive(Clone, Copy, Debug)]
pub struct PtpExchange {
    /// t1: sender transmit timestamp (sender clock)
    pub t1: Fraction,
    /// t2: receiver receive timestamp (receiver clock)
    pub t2: Fraction,
    /// t3: receiver reply timestamp (receiver clock)
    pub t3: Fraction,
    /// t4: sender receive timestamp (sender clock)
    pub t4: Fraction,
}

impl PtpExchange {
    /// Create a new PTP exchange.
    pub fn new(t1: Fraction, t2: Fraction, t3: Fraction, t4: Fraction) -> Self {
        PtpExchange { t1, t2, t3, t4 }
    }

    /// Compute the estimated offset: ((t2 - t1) - (t4 - t3)) / 2
    ///
    /// This is the standard IEEE 1588 offset formula.
    pub fn offset(&self) -> Fraction {
        let forward_delay = self.t2.sub(self.t1);
        let return_delay = self.t4.sub(self.t3);
        let diff = forward_delay.sub(return_delay);
        Fraction::new(diff.num, diff.den * 2)
    }

    /// Compute the estimated one-way delay: ((t2 - t1) + (t4 - t3)) / 2
    pub fn delay(&self) -> Fraction {
        let forward = self.t2.sub(self.t1);
        let ret = self.t4.sub(self.t3);
        let sum = forward.add(ret);
        Fraction::new(sum.num, sum.den * 2)
    }
}

/// PTP offset estimator that accumulates exchanges and computes filtered offset.
#[derive(Clone, Debug)]
pub struct PtpEstimator {
    exchanges: [Option<PtpExchange>; 16],
    count: usize,
    mode: PtpMode,
}

impl PtpEstimator {
    /// Create a new estimator with the given mode.
    pub fn new(mode: PtpMode) -> Self {
        PtpEstimator {
            exchanges: [None; 16],
            count: 0,
            mode,
        }
    }

    /// Record a PTP exchange.
    pub fn record(&mut self, exchange: PtpExchange) {
        let idx = self.count % 16;
        self.exchanges[idx] = Some(exchange);
        self.count += 1;
    }

    /// Compute the filtered (median) offset from recorded exchanges.
    /// Returns Fraction::ZERO if no exchanges recorded or mode is FreeRunning.
    pub fn estimated_offset(&self) -> Fraction {
        if self.mode == PtpMode::FreeRunning || self.count == 0 {
            return Fraction::ZERO;
        }

        let n = self.count.min(16);
        let mut offsets: [Fraction; 16] = [Fraction::ZERO; 16];
        let mut valid = 0usize;
        for i in 0..n {
            if let Some(ref ex) = self.exchanges[i] {
                offsets[valid] = ex.offset();
                valid += 1;
            }
        }

        if valid == 0 {
            return Fraction::ZERO;
        }

        // Simple insertion sort for median (max 16 elements)
        let mut sorted: [Fraction; 16] = offsets;
        for i in 1..valid {
            let key = sorted[i];
            let mut j = i;
            while j > 0 && sorted[j - 1] > key {
                sorted[j] = sorted[j - 1];
                j -= 1;
            }
            sorted[j] = key;
        }

        // Return median
        sorted[valid / 2]
    }

    /// Get the number of recorded exchanges.
    pub fn exchange_count(&self) -> usize {
        self.count
    }
}

/// Estimate the drift rate between local and reference clock.
///
/// Takes two (local, reference) pairs and computes the drift as a fraction.
pub fn estimate_drift(local1: Fraction, ref1: Fraction, local2: Fraction, ref2: Fraction) -> Fraction {
    let delta_local = local2.sub(local1);
    let delta_ref = ref2.sub(ref1);
    if delta_ref.num == 0 {
        return Fraction::ONE; // undefined, return 1
    }
    delta_local.mul(Fraction::new(delta_ref.den as i64, delta_ref.num.unsigned_abs() as u64))
}

/// Compute exponential weighted moving average correction.
///
/// Uses libm for f64 power if needed, but primary path is pure integer.
pub fn ewma_correction(prev: Fraction, measurement: Fraction, alpha: Fraction) -> Fraction {
    // result = alpha * measurement + (1 - alpha) * prev
    let one = Fraction::ONE;
    let weight_prev = one.sub(alpha);
    measurement.mul(alpha).add(prev.mul(weight_prev))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_offset_zero_delay() {
        // Symmetric 0-delay: all timestamps equal
        let t = Fraction::new(100, 1);
        let ex = PtpExchange::new(t, t, t, t);
        assert_eq!(ex.offset(), Fraction::ZERO);
    }

    #[test]
    fn test_offset_known() {
        // t1=0, t2=5, t3=5, t4=10: offset = ((5-0)-(10-5))/2 = 0, delay = 5
        let ex = PtpExchange::new(
            Fraction::new(0, 1),
            Fraction::new(5, 1),
            Fraction::new(5, 1),
            Fraction::new(10, 1),
        );
        assert_eq!(ex.offset(), Fraction::ZERO);
        assert_eq!(ex.delay(), Fraction::new(5, 1));
    }

    #[test]
    fn test_offset_asymmetric() {
        // t1=0, t2=10, t3=10, t4=12: offset = ((10-0)-(12-10))/2 = 4, delay = 6
        let ex = PtpExchange::new(
            Fraction::new(0, 1),
            Fraction::new(10, 1),
            Fraction::new(10, 1),
            Fraction::new(12, 1),
        );
        let offset = ex.offset();
        assert_eq!(offset, Fraction::new(4, 1));
    }
}

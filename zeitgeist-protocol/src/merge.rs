//! Zeitgeist merge module — re-exports and test utilities
//!
//! The merge laws are proven in the zeitgeist module tests:
//! - Commutativity: merge(a,b) == merge(b,a)
//! - Associativity: merge(merge(a,b),c) == merge(a,merge(b,c))
//! - Idempotency: merge(a,a) == a

pub use crate::zeitgeist::Zeitgeist;

#[cfg(test)]
mod laws {
    use crate::confidence::ConfidenceState;
    use crate::consensus::ConsensusState;
    use crate::precision::PrecisionState;
    use crate::temporal::{Phase, TemporalState};
    use crate::trajectory::{TrajectoryState, Trend};
    use crate::zeitgeist::Zeitgeist;
    use rand::Rng;
    use std::collections::BTreeMap;

    fn random_zeitgeist() -> Zeitgeist {
        let mut rng = rand::thread_rng();

        let bloom: [u8; 32] = {
            let mut b = [0u8; 32];
            rng.fill(&mut b[..]);
            b
        };

        Zeitgeist::new(
            PrecisionState::new(
                rng.gen_range(0.001..99999.0),
                rng.gen_range(0.0..1.0),
                rng.gen_bool(0.5),
            ),
            ConfidenceState::new(bloom, rng.gen(), rng.gen_range(0.0..1.0)),
            TrajectoryState::new(
                rng.gen_range(0.0..1.0),
                match rng.gen_range(0u8..4) {
                    0 => Trend::Stable,
                    1 => Trend::Rising,
                    2 => Trend::Falling,
                    _ => Trend::Chaotic,
                },
                rng.gen_range(-10.0..10.0),
            ),
            ConsensusState::new(rng.gen_range(0.0..1.0), rng.gen_range(0.0..1.0), {
                let mut m = BTreeMap::new();
                for _ in 0..rng.gen_range(0..5) {
                    m.insert(rng.gen(), rng.gen());
                }
                m
            }),
            TemporalState::new(
                rng.gen_range(0.0..1.0),
                match rng.gen_range(0u8..4) {
                    0 => Phase::Idle,
                    1 => Phase::Approaching,
                    2 => Phase::Snap,
                    _ => Phase::Hold,
                },
                rng.gen_range(0.0..1.0),
            ),
        )
    }

    #[test]
    fn merge_is_commutative() {
        for _ in 0..100 {
            let a = random_zeitgeist();
            let b = random_zeitgeist();
            assert_eq!(a.merge(&b), b.merge(&a), "Commutativity violated!");
        }
    }

    #[test]
    fn merge_is_associative() {
        for _ in 0..100 {
            let a = random_zeitgeist();
            let b = random_zeitgeist();
            let c = random_zeitgeist();
            assert_eq!(
                a.merge(&b).merge(&c),
                a.merge(&b.merge(&c)),
                "Associativity violated!"
            );
        }
    }

    #[test]
    fn merge_is_idempotent() {
        for _ in 0..100 {
            let a = random_zeitgeist();
            assert_eq!(a.merge(&a), a, "Idempotency violated!");
        }
    }

    #[test]
    fn cbor_roundtrip() {
        for _ in 0..50 {
            let zg = random_zeitgeist();
            let encoded = zg.encode();
            let decoded = Zeitgeist::decode(&encoded).unwrap();
            assert_eq!(zg, decoded, "CBOR roundtrip failed!");
        }
    }

    #[test]
    fn alignment_check_valid() {
        let zg = random_zeitgeist();
        let report = zg.check_alignment();
        assert!(
            report.aligned,
            "Random zeitgeist should be aligned: {:?}",
            report.violations
        );
    }

    #[test]
    fn alignment_detects_violation() {
        let mut zg = random_zeitgeist();
        zg.precision.deadband = -1.0; // Invalid
        zg.confidence.certainty = 2.0; // Invalid
        zg.trajectory.hurst = 1.5; // Invalid
        zg.temporal.beat_pos = -0.5; // Invalid
        let report = zg.check_alignment();
        assert!(!report.aligned);
        assert!(
            report.violations.len() >= 4,
            "Expected 4+ violations, got: {:?}",
            report.violations
        );
    }
}

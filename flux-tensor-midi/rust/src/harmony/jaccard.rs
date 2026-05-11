/// Jaccard similarity for flux channel sets.
///
/// Measures the overlap between two sets of active channels (or channel
/// properties) as a harmonic distance metric.

use crate::core::FluxVector;

/// Compute the Jaccard index between two sets of active indices.
///
/// `J(A, B) = |A ∩ B| / |A ∪ B|`
///
/// Returns 0.0 when both sets are empty (no active channels in either).
pub fn jaccard_active(a: &FluxVector, b: &FluxVector) -> f64 {
    let a_active: Vec<usize> = a
        .channels
        .iter()
        .enumerate()
        .filter(|(_, ch)| ch.intensity > 0)
        .map(|(i, _)| i)
        .collect();

    let b_active: Vec<usize> = b
        .channels
        .iter()
        .enumerate()
        .filter(|(_, ch)| ch.intensity > 0)
        .map(|(i, _)| i)
        .collect();

    if a_active.is_empty() && b_active.is_empty() {
        return 1.0; // two silences are "the same"
    }

    let intersection_count = a_active
        .iter()
        .filter(|i| b_active.contains(i))
        .count();

    let union_count = a_active.len() + b_active.len() - intersection_count;

    if union_count == 0 {
        return 0.0;
    }

    intersection_count as f64 / union_count as f64
}

/// Weighted Jaccard similarity that considers intensity values, not just
/// active/inactive status.
///
/// Uses the minimum-sum-over-maximum-sum formulation:
/// `J_w(A, B) = Σ min(A_i, B_i) / Σ max(A_i, B_i)`
/// where intensities are normalized to [0, 1].
pub fn weighted_jaccard(a: &FluxVector, b: &FluxVector) -> f64 {
    let mut sum_min = 0.0;
    let mut sum_max = 0.0;

    for (ch_a, ch_b) in a.channels.iter().zip(b.channels.iter()) {
        let na = ch_a.normalized();
        let nb = ch_b.normalized();
        sum_min += na.min(nb);
        sum_max += na.max(nb);
    }

    if sum_max == 0.0 {
        return 1.0;
    }

    sum_min / sum_max
}

/// Harmonic distance between two vectors as 1 - Jaccard (dissimilarity).
#[inline]
pub fn harmonic_distance(a: &FluxVector, b: &FluxVector) -> f64 {
    1.0 - jaccard_active(a, b)
}

/// Weighted harmonic distance.
#[inline]
pub fn weighted_harmonic_distance(a: &FluxVector, b: &FluxVector) -> f64 {
    1.0 - weighted_jaccard(a, b)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::core::FluxChannel;

    fn make_flux(active: &[usize]) -> FluxVector {
        let mut chs = [FluxChannel::new(0); 9];
        for &i in active {
            chs[i] = FluxChannel::new(100);
        }
        FluxVector::new(chs)
    }

    #[test]
    fn test_jaccard_identical() {
        let a = make_flux(&[0, 1, 2]);
        let b = make_flux(&[0, 1, 2]);
        assert!((jaccard_active(&a, &b) - 1.0).abs() < 1e-10);
    }

    #[test]
    fn test_jaccard_disjoint() {
        let a = make_flux(&[0, 1]);
        let b = make_flux(&[3, 4]);
        assert!((jaccard_active(&a, &b) - 0.0).abs() < 1e-10);
    }

    #[test]
    fn test_jaccard_partial() {
        let a = make_flux(&[0, 1, 2]);
        let b = make_flux(&[1, 2, 3]);
        // intersection = {1, 2} = 2, union = {0, 1, 2, 3} = 4
        assert!((jaccard_active(&a, &b) - 0.5).abs() < 1e-10);
    }

    #[test]
    fn test_jaccard_both_silent() {
        let a = make_flux(&[]);
        let b = make_flux(&[]);
        assert!((jaccard_active(&a, &b) - 1.0).abs() < 1e-10);
    }

    #[test]
    fn test_weighted_jaccard_full() {
        let a = FluxVector::uniform(127);
        let b = FluxVector::uniform(127);
        assert!((weighted_jaccard(&a, &b) - 1.0).abs() < 1e-10);
    }

    #[test]
    fn test_weighted_jaccard_half() {
        let a = FluxVector::uniform(127);
        let b = FluxVector::uniform(64);
        let wj = weighted_jaccard(&a, &b);
        // With uniform intensities, all pairs have the same ratio
        assert!(wj > 0.0 && wj < 1.0);
    }

    #[test]
    fn test_harmonic_distance() {
        let a = make_flux(&[0, 1]);
        let b = make_flux(&[0, 1]);
        assert!((harmonic_distance(&a, &b) - 0.0).abs() < 1e-10);
    }

    #[test]
    fn test_harmonic_distance_max() {
        let a = make_flux(&[0]);
        let b = make_flux(&[1]);
        assert!((harmonic_distance(&a, &b) - 1.0).abs() < 1e-10);
    }
}

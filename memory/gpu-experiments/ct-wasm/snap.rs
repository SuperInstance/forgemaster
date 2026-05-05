use crate::triple::Triple;

/// Find the index of the nearest triple to (qx, qy) using an O(log n)
/// binary search on the angle-sorted triple array.
///
/// All normalised triple points lie on the unit circle, so they have a
/// natural 1-D ordering by θ = atan2(y, x).  We binary-search for the
/// insertion position of the query angle, then compare the two (or three)
/// neighbouring candidates to pick the true nearest.
pub fn snap_by_angle(qx: f64, qy: f64, triples: &[Triple]) -> usize {
    let n = triples.len();
    if n == 0 {
        return 0;
    }
    if n == 1 {
        return 0;
    }

    let q_theta = qy.atan2(qx);

    // `partition_point` is a stable binary search: returns the first index
    // where the predicate is false, i.e. the insertion point of q_theta.
    let pos = triples.partition_point(|t| t.angle() < q_theta);

    // Examine up to three candidates around the insertion point,
    // including wrap-around at the ±π boundary.
    let candidates: [usize; 3] = [
        if pos == 0 { n - 1 } else { pos - 1 },
        pos.min(n - 1),
        (pos + 1).min(n - 1),
    ];

    candidates
        .iter()
        .copied()
        .min_by(|&a, &b| {
            let da = dist2_to_triple(qx, qy, &triples[a]);
            let db = dist2_to_triple(qx, qy, &triples[b]);
            da.partial_cmp(&db).unwrap_or(std::cmp::Ordering::Equal)
        })
        .unwrap()
}

/// O(n) brute-force snap — used for the performance comparison panel.
pub fn snap_brute(qx: f64, qy: f64, triples: &[Triple]) -> usize {
    triples
        .iter()
        .enumerate()
        .min_by(|(_, a), (_, b)| {
            let da = dist2_to_triple(qx, qy, a);
            let db = dist2_to_triple(qx, qy, b);
            da.partial_cmp(&db).unwrap_or(std::cmp::Ordering::Equal)
        })
        .map(|(i, _)| i)
        .unwrap_or(0)
}

/// Squared Euclidean distance from (qx, qy) to the normalised point of t.
#[inline]
fn dist2_to_triple(qx: f64, qy: f64, t: &Triple) -> f64 {
    let (tx, ty) = t.normalized();
    let dx = qx - tx;
    let dy = qy - ty;
    dx * dx + dy * dy
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::triple::generate_triples;

    #[test]
    fn snap_matches_brute() {
        let ts = generate_triples(500);
        // Query a grid of angles and verify binary-search agrees with brute force.
        for i in 0..=16 {
            let theta = (i as f64) * std::f64::consts::FRAC_PI_2 / 16.0;
            let qx = theta.cos();
            let qy = theta.sin();
            let bs = snap_by_angle(qx, qy, &ts);
            let bf = snap_brute(qx, qy, &ts);
            // Both should give the same minimum distance (index may differ for ties)
            let d_bs = dist2_to_triple(qx, qy, &ts[bs]);
            let d_bf = dist2_to_triple(qx, qy, &ts[bf]);
            assert!(
                (d_bs - d_bf).abs() < 1e-12,
                "mismatch at theta={:.4}: bs idx={bs} d={d_bs:.6e}, bf idx={bf} d={d_bf:.6e}",
                theta
            );
        }
    }
}

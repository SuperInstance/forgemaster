use crate::snap::snap_by_angle;
use crate::triple::Triple;

/// Walk a closed angular path on the snap manifold.
///
/// `angle_deltas` is an array of radian steps.  A closed path should have
/// deltas that sum to approximately zero.  At each step we snap to the
/// nearest triple on the unit circle; the holonomy is the Euclidean
/// distance between the final snapped position and the starting position.
///
/// A non-zero return value indicates the manifold's discrete structure
/// introduces a rotational "phase slip" — the geometric analogue of
/// holonomy in differential geometry.
pub fn measure_holonomy(angle_deltas: &[f64], triples: &[Triple]) -> f64 {
    if triples.is_empty() || angle_deltas.is_empty() {
        return 0.0;
    }

    // Anchor: snap the origin of the path to the nearest triple to (1, 0)
    let start_idx = snap_by_angle(1.0, 0.0, triples);
    let (sx, sy) = triples[start_idx].normalized();

    // Walk the path, snapping at every step
    let mut current_angle = 0.0_f64;
    let mut end_x = sx;
    let mut end_y = sy;

    for &delta in angle_deltas {
        current_angle += delta;
        let qx = current_angle.cos();
        let qy = current_angle.sin();
        let idx = snap_by_angle(qx, qy, triples);
        let (px, py) = triples[idx].normalized();
        end_x = px;
        end_y = py;
    }

    // Holonomy = displacement of end from start in normalised coordinates
    let dx = end_x - sx;
    let dy = end_y - sy;
    (dx * dx + dy * dy).sqrt()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::triple::generate_triples;

    #[test]
    fn empty_path_is_zero() {
        let ts = generate_triples(100);
        assert_eq!(measure_holonomy(&[], &ts), 0.0);
    }

    #[test]
    fn single_full_rotation_small() {
        // A path of 360 equal steps summing to 2π should be approximately closed.
        let ts = generate_triples(200);
        let n = 360usize;
        let step = 2.0 * std::f64::consts::PI / n as f64;
        let deltas: Vec<f64> = (0..n).map(|_| step).collect();
        let h = measure_holonomy(&deltas, &ts);
        // Holonomy is expected to be small but non-zero due to snap discretisation
        assert!(h < 0.5, "holonomy {h} unexpectedly large");
    }
}

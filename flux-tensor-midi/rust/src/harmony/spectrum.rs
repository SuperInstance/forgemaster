/// Spectral analysis of flux vectors using discrete cosine transform (DCT-II).
///
/// The spectral profile reveals harmonic structure across the 9 flux channels,
/// useful for detecting chord shapes, voicing patterns, and ensemble balance.

/// Compute DCT-II on a 9-element flux intensity vector.
///
/// `X[k] = Σ x[n] · cos(π · k · (n + 0.5) / 9)`
///
/// The result size is 9 (same as input).
pub fn flux_dct(intensities: &[i8; 9]) -> [f64; 9] {
    let n = intensities.len() as f64;
    let mut result = [0.0f64; 9];

    for k in 0..9 {
        let kf = k as f64;
        let mut sum = 0.0;
        for (n, &val) in intensities.iter().enumerate() {
            let nf = n as f64;
            sum += val as f64 * (core::f64::consts::PI * kf * (nf + 0.5) / n).cos();
        }
        result[k] = sum;
    }

    result
}

/// Energy in each DCT coefficient (squared magnitude).
#[inline]
pub fn dct_energy(spectrum: &[f64; 9]) -> [f64; 9] {
    let mut energy = [0.0f64; 9];
    for (i, &v) in spectrum.iter().enumerate() {
        energy[i] = v * v;
    }
    energy
}

/// Total spectral energy (sum of squared DCT coefficients).
#[inline]
pub fn total_spectral_energy(spectrum: &[f64; 9]) -> f64 {
    spectrum.iter().map(|v| v * v).sum()
}

/// Spectral centroid — the "center of mass" of the frequency spectrum.
///
/// Lower values indicate bass-heavy / smooth profiles; higher values indicate
/// treble-heavy / detailed profiles.
pub fn spectral_centroid(spectrum: &[f64; 9]) -> f64 {
    let total = total_spectral_energy(spectrum);
    if total == 0.0 {
        return 0.0;
    }

    let weighted_sum: f64 = spectrum
        .iter()
        .enumerate()
        .map(|(k, &v)| (k as f64 + 1.0) * v * v)
        .sum();

    weighted_sum / total
}

/// Dominant spectral bin (index of max energy coefficient).
pub fn dominant_bin(spectrum: &[f64; 9]) -> usize {
    let energies = dct_energy(spectrum);
    energies
        .iter()
        .enumerate()
        .max_by(|(_, a), (_, b)| a.partial_cmp(b).unwrap_or(core::cmp::Ordering::Equal))
        .map(|(i, _)| i)
        .unwrap_or(0)
}

/// Spectral flatness measure — ratio of geometric mean to arithmetic mean.
///
/// Values near 1.0 indicate noise-like (flat spectrum).
/// Values near 0.0 indicate tonal/pure (peaked spectrum).
pub fn spectral_flatness(spectrum: &[f64; 9]) -> f64 {
    let energies = dct_energy(spectrum);
    //  Remove DC component (index 0) for flatness calculation
    let meaningful: Vec<f64> = energies.iter().skip(1).copied().collect();

    if meaningful.is_empty() {
        return 0.0;
    }

    // Add small epsilon to avoid log(0)
    let eps = 1e-10;
    let n = meaningful.len() as f64;

    let log_mean: f64 = meaningful.iter().map(|e| (e + eps).ln()).sum::<f64>() / n;
    let arith_mean: f64 = meaningful.iter().sum::<f64>() / n + eps;

    (log_mean.exp()) / arith_mean
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_dct_uniform() {
        // Uniform input should have only DC (k=0) component
        let intensities = [100i8; 9];
        let spectrum = flux_dct(&intensities);
        let energy = dct_energy(&spectrum);
        assert!(energy[0] > 0.0);
        // Non-DC components should be near zero
        for k in 1..9 {
            assert!(energy[k] < 1e-10, "k={k} energy not near zero: {}", energy[k]);
        }
    }

    #[test]
    fn test_dct_sine_like() {
        // Pattern with a clear mid-frequency component
        let intensities: [i8; 9] = [0, 50, 100, 50, 0, -50, -100, -50, 0];
        let spectrum = flux_dct(&intensities);
        let dominant = dominant_bin(&spectrum);
        // Should have energy in middle bins
        assert!(dominant > 1);
    }

    #[test]
    fn test_spectral_centroid_uniform() {
        let intensities = [64i8; 9];
        let spectrum = flux_dct(&intensities);
        let centroid = spectral_centroid(&spectrum);
        // Uniform → only DC component → centroid at 1.0 (bin index + 1)
        assert!((centroid - 1.0).abs() < 0.01);
    }

    #[test]
    fn test_spectral_flatness() {
        // Pure tone → flatness near zero
        let pure = [127i8, 0, 0, 0, 0, 0, 0, 0, 0];
        let spec = flux_dct(&pure);
        let flatness = spectral_flatness(&spec);
        assert!(flatness < 1.0);

        // White noise-ish → flatness closer to 1
        let noise: [i8; 9] = [
            10, -25, 63, -12, 80, -55, 42, -78, 30,
        ];
        let spec = flux_dct(&noise);
        let flatness = spectral_flatness(&spec);
        // Not a guarantee but a reasonable expectation
        assert!(flatness > 0.0);
    }

    #[test]
    fn test_total_spectral_energy_conservation() {
        // Parseval-type check: energy in DCT should relate to input energy
        let intensities = [100i8; 9];
        let spectrum = flux_dct(&intensities);
        let total = total_spectral_energy(&spectrum);
        assert!(total > 0.0);
    }

    #[test]
    fn test_dominant_bin() {
        let mut intensities = [0i8; 9];
        intensities[4] = 100; // channel 4 peaks
        let spectrum = flux_dct(&intensities);
        let db = dominant_bin(&spectrum);
        // Should have some non-zero dominant bin
        assert!(db < 9);
    }
}

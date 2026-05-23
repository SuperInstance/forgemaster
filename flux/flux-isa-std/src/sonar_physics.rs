/// Sonar physics calculations — Mackenzie 1981 sound speed equation
/// and simplified Francois-Garrison absorption model.
///
/// Designed for ARM Cortex-A53/A72 — full f64, no FPU limitations.

/// Mackenzie (1981) equation for speed of sound in seawater.
///
/// Parameters:
/// - `temp`: Temperature in °C (range 2–30)
/// - `salinity`: Salinity in PSU (range 25–40)
/// - `depth`: Depth in meters (range 0–8000)
///
/// Returns speed of sound in m/s.
pub fn sound_speed(temp: f64, salinity: f64, depth: f64) -> f64 {
    // Mackenzie 1981: c = 1448.96 + 4.591T - 5.304e-2 T² + 2.374e-4 T³
    //                        + 1.340(S-35) + 1.630e-2 D + 1.675e-7 D²
    //                        - 1.025e-2 T(S-35) - 7.139e-13 T D³
    let t = temp;
    let s = salinity;
    let d = depth;

    1448.96
        + 4.591 * t
        - 5.304e-2 * t * t
        + 2.374e-4 * t * t * t
        + 1.340 * (s - 35.0)
        + 1.630e-2 * d
        + 1.675e-7 * d * d
        - 1.025e-2 * t * (s - 35.0)
        - 7.139e-13 * t * d * d * d
}

/// Simplified Francois-Garrison absorption coefficient.
///
/// Parameters:
/// - `freq_khz`: Frequency in kHz
/// - `depth`: Depth in meters
/// - `temp`: Temperature in °C
/// - `salinity`: Salinity in PSU
///
/// Returns absorption in dB/km.
pub fn absorption(freq_khz: f64, depth: f64, temp: f64, salinity: f64) -> f64 {
    let f = freq_khz;
    let t = temp;
    let d = depth;
    let s = salinity;

    // Francois-Garrison simplified (1982)
    // Relaxation frequencies
    let f1 = 0.78 * (s / 35.0).sqrt() * (t / 26.0).exp(); // boric acid (kHz)
    let f2 = 42.0 * (t / 17.0).exp(); // magnesium sulfate (kHz)

    // pH contribution
    let a = (8.86 / t).exp();
    let b = (-(d) / 2000.0).exp(); // depth correction

    // Boric acid contribution
    let a1 = 0.106 * ((f1 * f1 - f * f) / (f1 * f1 + f * f)).abs()
        * f1
        * f
        / (f1 * f1 + f * f).max(1e-10);
    let p1 = 1.0;

    // Magnesium sulfate contribution
    let a2 = 0.52 * (1.0 + t / 43.0) * (s / 35.0)
        * ((f2 * f2 - f * f) / (f2 * f2 + f * f)).abs()
        * f2
        * f
        / (f2 * f2 + f * f).max(1e-10);
    let p2 = b;

    // Pure water absorption
    let a3 = 0.00049 * f * f;

    (a1 * p1 + a2 * p2 + a3) * a
}

/// Wavelength in meters for a given frequency and conditions.
pub fn wavelength(freq_khz: f64, temp: f64, salinity: f64, depth: f64) -> f64 {
    let c = sound_speed(temp, salinity, depth);
    let freq_hz = freq_khz * 1000.0;
    c / freq_hz
}

/// One-way travel time in seconds for a given depth (round-trip / 2).
/// Assumes vertical propagation through a uniform medium.
pub fn travel_time(distance_m: f64, temp: f64, salinity: f64, depth: f64) -> f64 {
    let c = sound_speed(temp, salinity, depth);
    distance_m / c
}

/// Convenience wrapper for sonar calculations
pub struct SonarPhysics;

impl SonarPhysics {
    pub fn sound_speed(temp: f64, salinity: f64, depth: f64) -> f64 {
        sound_speed(temp, salinity, depth)
    }

    pub fn absorption(freq_khz: f64, depth: f64, temp: f64, salinity: f64) -> f64 {
        absorption(freq_khz, depth, temp, salinity)
    }

    pub fn wavelength(freq_khz: f64, temp: f64, salinity: f64, depth: f64) -> f64 {
        wavelength(freq_khz, temp, salinity, depth)
    }

    pub fn travel_time(distance_m: f64, temp: f64, salinity: f64, depth: f64) -> f64 {
        travel_time(distance_m, temp, salinity, depth)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sound_speed_surface() {
        // Fresh-ish water at surface: ~1482 m/s at 20°C, 35 PSU, 0m
        let c = sound_speed(20.0, 35.0, 0.0);
        assert!(c > 1500.0 && c < 1530.0, "Sound speed {} out of expected range", c);
    }

    #[test]
    fn test_sound_speed_deep() {
        // Deep water: should be faster due to pressure
        let c_surface = sound_speed(10.0, 35.0, 0.0);
        let c_deep = sound_speed(10.0, 35.0, 4000.0);
        assert!(c_deep > c_surface, "Deep water should have higher sound speed");
    }

    #[test]
    fn test_wavelength() {
        // At 12 kHz, ~1500 m/s → λ ≈ 0.125m
        let wl = wavelength(12.0, 10.0, 35.0, 0.0);
        assert!(wl > 0.10 && wl < 0.15, "Wavelength {} out of expected range", wl);
    }

    #[test]
    fn test_travel_time() {
        // 1500m at ~1500 m/s → ~1 second
        let tt = travel_time(1500.0, 10.0, 35.0, 0.0);
        assert!((tt - 1.0).abs() < 0.05, "Travel time {} not close to 1.0s", tt);
    }

    #[test]
    fn test_absorption_positive() {
        let a = absorption(100.0, 0.0, 10.0, 35.0);
        assert!(a > 0.0, "Absorption should be positive");
    }
}

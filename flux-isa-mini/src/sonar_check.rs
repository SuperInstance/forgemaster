//! Built-in sonar constraint checks — const-evaluated bounds where possible.
//!
//! The microcontroller doesn't compute the Mackenzie equation;
//! it validates pre-computed bounds for the deployment environment.

/// Valid frequency range for common sonar systems (kHz).
pub const SONAR_FREQ_MIN_KHZ: f64 = 1.0;
pub const SONAR_FREQ_MAX_KHZ: f64 = 500.0;

/// Standard seawater sound speed bounds (m/s) — Mackenzie 1981 extremes at
/// 0–1000m depth, 0–35‰ salinity, -2–30°C.
pub const SOUND_SPEED_MIN: f64 = 1430.0;
pub const SOUND_SPEED_MAX: f64 = 1560.0;

/// Check measured sound speed against Mackenzie bounds.
///
/// Returns `true` if `min <= c <= max`. For standard deployments use
/// SOUND_SPEED_MIN / SOUND_SPEED_MAX as defaults.
#[inline(always)]
pub const fn check_sound_speed(c: f64, min: f64, max: f64) -> bool {
    c >= min && c <= max
}

/// Check depth against maximum rated depth for sensor housing.
///
/// Returns `true` if `depth <= max_depth`.
#[inline(always)]
pub const fn check_depth_pressure(depth: f64, max_depth: f64) -> bool {
    depth >= 0.0 && depth <= max_depth
}

/// Check sonar frequency is in valid operating range.
///
/// Returns `true` if frequency is within [1, 500] kHz.
#[inline(always)]
pub const fn check_frequency_range(freq_khz: f64) -> bool {
    freq_khz >= SONAR_FREQ_MIN_KHZ && freq_khz <= SONAR_FREQ_MAX_KHZ
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sound_speed_in_range() {
        assert!(check_sound_speed(1500.0, SOUND_SPEED_MIN, SOUND_SPEED_MAX));
    }

    #[test]
    fn sound_speed_out_of_range() {
        assert!(!check_sound_speed(1400.0, SOUND_SPEED_MIN, SOUND_SPEED_MAX));
    }

    #[test]
    fn depth_ok() {
        assert!(check_depth_pressure(50.0, 200.0));
    }

    #[test]
    fn depth_negative() {
        assert!(!check_depth_pressure(-1.0, 200.0));
    }

    #[test]
    fn freq_valid() {
        assert!(check_frequency_range(200.0));
    }
}

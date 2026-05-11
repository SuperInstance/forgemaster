/// Core types for FLUX-Tensor-MIDI.
///
/// # Flux Channels
///
/// A room has up to 9 FluxChannels, each representing a musician or voice
/// in the PLATO room. Each channel carries a signed intensity value and
/// an optional cluster assignment for harmonic grouping.

use crate::MidiEvent;
use core::cmp::Ordering;
use core::fmt;

/// 1/√3 — the Eisenstein lattice covering radius, computed at compile time.
pub(crate) const INV_SQRT_3: f64 = 0.5773502691896257645091487805019574556476;

// ---------------------------------------------------------------------------
// FluxVector — the core tensor type
// ---------------------------------------------------------------------------

/// Intensity bounds for a single flux channel.
pub const FLUX_CHANNEL_MIN: i8 = -128;
pub const FLUX_CHANNEL_MAX: i8 = 127;

/// A single flux channel — one musician's expressive intensity.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct FluxChannel {
    /// Signed intensity in [-128, 127] — musical energy.
    pub intensity: i8,
    /// Optional cluster id for harmonic grouping.
    pub cluster: Option<u8>,
}

impl FluxChannel {
    /// Create a new FluxChannel with the given intensity, clamped to bounds.
    #[inline]
    pub fn new(intensity: i8) -> Self {
        FluxChannel {
            intensity,
            cluster: None,
        }
    }

    /// Create a FluxChannel with both intensity and cluster assignment.
    #[inline]
    pub fn with_cluster(intensity: i8, cluster: u8) -> Self {
        FluxChannel {
            intensity,
            cluster: Some(cluster),
        }
    }

    /// Absolute intensity value.
    #[inline]
    pub fn magnitude(self) -> u8 {
        self.intensity.unsigned_abs()
    }

    /// Intensity scaled to [0.0, 1.0].
    #[inline]
    pub fn normalized(self) -> f64 {
        (self.intensity as f64 + 128.0) / 255.0
    }
}

/// A 9-channel flux vector representing all musicians in a room.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct FluxVector {
    /// The 9 channel intensities.
    pub channels: [FluxChannel; 9],
}

impl FluxVector {
    /// Create a new FluxVector from 9 channel intensities.
    #[inline]
    pub fn new(channels: [FluxChannel; 9]) -> Self {
        FluxVector { channels }
    }

    /// Create a FluxVector with all channels set to the given intensity.
    #[inline]
    pub fn uniform(intensity: i8) -> Self {
        FluxVector {
            channels: [FluxChannel::new(intensity); 9],
        }
    }

    /// Sum of squared intensities — total energy in the room.
    pub fn energy(self) -> u32 {
        self.channels
            .iter()
            .map(|c| c.intensity as i32)
            .map(|i| (i * i) as u32)
            .sum()
    }

    /// L2 distance between two flux vectors.
    pub fn l2_distance(self, other: &FluxVector) -> f64 {
        self.channels
            .iter()
            .zip(other.channels.iter())
            .map(|(a, b)| {
                let d = a.intensity as f64 - b.intensity as f64;
                d * d
            })
            .sum::<f64>()
            .sqrt()
    }

    /// L∞ (Chebyshev) distance — max absolute channel difference.
    pub fn chebyshev_distance(self, other: &FluxVector) -> i8 {
        self.channels
            .iter()
            .zip(other.channels.iter())
            .map(|(a, b)| (a.intensity as i16 - b.intensity as i16).unsigned_abs() as i8)
            .max()
            .unwrap_or(0)
    }

    /// Dot product with another flux vector.
    pub fn dot(self, other: &FluxVector) -> i64 {
        self.channels
            .iter()
            .zip(other.channels.iter())
            .map(|(a, b)| a.intensity as i64 * b.intensity as i64)
            .sum()
    }

    /// Scalar multiply all channels (saturating).
    #[inline]
    pub fn scale(self, factor: f64) -> Self {
        let mut scaled = self;
        for ch in &mut scaled.channels {
            let v = (ch.intensity as f64 * factor).round().clamp(-128.0, 127.0);
            ch.intensity = v as i8;
        }
        scaled
    }

    /// Return channels assigned to a specific cluster.
    pub fn cluster_channels(&self, cluster: u8) -> Vec<FluxChannel> {
        self.channels
            .iter()
            .copied()
            .filter(|c| c.cluster == Some(cluster))
            .collect()
    }

    /// Mean intensity across all channels.
    pub fn mean(self) -> f64 {
        let sum: i64 = self.channels.iter().map(|c| c.intensity as i64).sum();
        sum as f64 / 9.0
    }

    /// Standard deviation of channel intensities.
    pub fn std_dev(self) -> f64 {
        let m = self.mean();
        let var: f64 = self
            .channels
            .iter()
            .map(|c| {
                let d = c.intensity as f64 - m;
                d * d
            })
            .sum::<f64>()
            / 9.0;
        var.sqrt()
    }
}

impl fmt::Display for FluxVector {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "[")?;
        for (i, ch) in self.channels.iter().enumerate() {
            if i > 0 {
                write!(f, ",")?;
            }
            write!(f, "{}", ch.intensity)?;
        }
        write!(f, "]")
    }
}

// ---------------------------------------------------------------------------
// TZeroClock — Thermodynamic Zero Clock with EWMA
// ---------------------------------------------------------------------------

/// A Thermodynamic-Zero (T-0) clock using Exponential Weighted Moving Average
/// for temporal smoothing at absolute zero (no thermal noise).
///
/// The EWMA formula:
///   `ema = α · tick + (1 − α) · ema`
///
/// Where `α` is derived from the half-life parameter.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct TZeroClock {
    /// Current smoothed tick value.
    pub tick: f64,
    /// EWMA of prior ticks.
    pub ema: f64,
    /// Smoothing factor α in (0, 1].
    alpha: f64,
    /// Number of ticks recorded.
    pub n_ticks: u64,
}

impl TZeroClock {
    /// Create a new TZeroClock with the given alpha.
    ///
    /// `alpha` must be in (0, 1] — higher values give more weight to recent ticks.
    /// Values near 0.01–0.1 are typical for smoothing; values near 1.0 for
    /// instant response.
    #[inline]
    pub fn new(alpha: f64) -> Self {
        assert!(
            alpha > 0.0 && alpha <= 1.0,
            "alpha must be in (0, 1], got {alpha}"
        );
        TZeroClock {
            tick: 0.0,
            ema: 0.0,
            alpha,
            n_ticks: 0,
        }
    }

    /// Create a TZeroClock from a half-life: the number of ticks for the
    /// weight of old samples to decay by 50%.
    ///
    /// `α = 1 − exp(ln(0.5) / half_life)`
    #[inline]
    pub fn with_half_life(half_life: f64) -> Self {
        assert!(half_life > 0.0, "half_life must be positive");
        let alpha = 1.0 - (0.5_f64.ln() / half_life).exp();
        TZeroClock::new(alpha)
    }

    /// Record a tick at the given value, updating the EWMA.
    pub fn record(&mut self, tick: f64) -> f64 {
        self.tick = tick;
        self.n_ticks += 1;
        if self.n_ticks == 1 {
            self.ema = tick;
        } else {
            self.ema = self.alpha * tick + (1.0 - self.alpha) * self.ema;
        }
        self.ema
    }

    /// Record a tick with the current time.
    #[inline]
    pub fn tick(&mut self, now: f64) -> f64 {
        self.record(now)
    }

    /// The difference between the current tick and the EWMA — instantaneous
    /// deviation from the smoothed baseline.
    #[inline]
    pub fn deviation(&self) -> f64 {
        self.tick - self.ema
    }

    /// Momentum: rate of change of the EWMA over the last update.
    #[inline]
    pub fn momentum(&self, prior_ema: f64) -> f64 {
        self.ema - prior_ema
    }

    /// Get the alpha smoothing factor.
    #[inline]
    pub fn alpha(&self) -> f64 {
        self.alpha
    }

    /// Reset the clock to initial state.
    #[inline]
    pub fn reset(&mut self) {
        self.tick = 0.0;
        self.ema = 0.0;
        self.n_ticks = 0;
    }
}

impl Default for TZeroClock {
    /// Alpha = 0.1 for moderate smoothing.
    fn default() -> Self {
        TZeroClock::new(0.1)
    }
}

impl fmt::Display for TZeroClock {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "TZero(tick={:.4}, ema={:.4}, α={:.4}, n={})",
            self.tick, self.ema, self.alpha, self.n_ticks
        )
    }
}

// ---------------------------------------------------------------------------
// RoomMusician — a musician in a PLATO room
// ---------------------------------------------------------------------------

/// A musician in a PLATO room, carrying a flux vector and a T-0 clock.
///
/// Each musician can receive MIDI events and express through their flux channel.
#[derive(Debug, Clone)]
pub struct RoomMusician {
    /// Name or identifier for this musician.
    pub name: String,
    /// Channel index (0–8) in the room's flux vector.
    pub channel: usize,
    /// The musician's T-0 clock for temporal tracking.
    pub clock: TZeroClock,
    /// Intensity target (set by MIDI events or ensemble).
    pub target: i8,
    /// Whether the musician is actively playing.
    pub active: bool,
}

impl RoomMusician {
    /// Create a new RoomMusician with the given name and channel index.
    #[inline]
    pub fn new(name: &str, channel: usize) -> Self {
        assert!(channel < 9, "channel must be 0..=8");
        RoomMusician {
            name: name.to_string(),
            channel,
            clock: TZeroClock::default(),
            target: 0,
            active: false,
        }
    }

    /// Create a RoomMusician with a custom T-0 clock.
    #[inline]
    pub fn with_clock(name: &str, channel: usize, clock: TZeroClock) -> Self {
        assert!(channel < 9, "channel must be 0..=8");
        RoomMusician {
            name: name.to_string(),
            channel,
            clock,
            target: 0,
            active: false,
        }
    }

    /// Process a MIDI event, updating target intensity and clock.
    pub fn receive_midi(&mut self, event: &MidiEvent, now: f64) {
        self.clock.tick(now);
        self.target = event.velocity as i8;
        self.active = event.velocity > 0;
    }

    /// Convert the musician's current state into a FluxChannel.
    #[inline]
    pub fn flux_channel(&self) -> FluxChannel {
        FluxChannel::new(self.target)
    }

    /// Express the musician's current state into the given flux vector
    /// (modifies in-place at self.channel).
    pub fn express_into(&self, flux: &mut FluxVector) {
        flux.channels[self.channel] = self.flux_channel();
    }
}

impl fmt::Display for RoomMusician {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "{}[ch={}] target={} active={} clock={}",
            self.name, self.channel, self.target, self.active, self.clock
        )
    }
}

// ---------------------------------------------------------------------------
// Eisenstein Snap — rhythmic classification via covering radius
// ---------------------------------------------------------------------------

/// Eisenstein snap interval ratio.
///
/// Represented as a rational `p/q` mapped to the Eisenstein integer lattice.
/// The covering radius `1/√3` determines the maximal rhythmic deviation
/// before a snap reclassifies.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct SnapRatio {
    pub p: u32,
    pub q: u32,
}

impl SnapRatio {
    /// Create a new SnapRatio. `q` must be > 0.
    #[inline]
    pub fn new(p: u32, q: u32) -> Self {
        assert!(q > 0, "SnapRatio denominator must be > 0");
        SnapRatio { p, q }
    }

    /// The ratio as a floating-point value.
    #[inline]
    pub fn value(self) -> f64 {
        self.p as f64 / self.q as f64
    }

    /// Distance to another SnapRatio in the Eisenstein lattice.
    ///
    /// Uses the Euclidean metric on the lattice embedding:
    /// `d = |p/q − a/b| / (1/√(3))`
    pub fn lattice_distance(self, other: SnapRatio) -> f64 {
        let diff = (self.value() - other.value()).abs();
        diff * INV_SQRT_3.recip()
    }

    /// Check whether this ratio is within the covering radius of another.
    ///
    /// The Eisenstein covering radius `1/√3` ≈ 0.577 means almost any
    ///   /// Note: `lattice_distance` uses the standard Eisenstein radius, but
    /// `snaps_to` also verifies the raw value difference is musically plausible.
    #[inline]
    pub fn snaps_to(self, other: SnapRatio) -> bool {
        // The lattice distance must be within the covering radius
        // AND the raw ratio difference must be musically plausible (< 30%)
        let raw_diff = (self.value() - other.value()).abs();
        self.lattice_distance(other) <= 1.0 && raw_diff < 0.3
    }

    /// Classify the rhythmic category of this snap ratio.
    pub fn classify(self) -> SnapClass {
        let v = self.value();
        if v < 0.001 {
            SnapClass::Rest
        } else if (v - 1.0).abs() < 0.01 {
            SnapClass::Beat
        } else if v > 0.9 && v < 1.1 {
            SnapClass::Beat
        } else if v > 0.45 && v < 0.55 {
            SnapClass::Half
        } else if (v - 2.0).abs() < 0.01 {
            SnapClass::Double
        } else if v < 0.5 {
            SnapClass::Subdivision
        } else if v > 2.0 {
            SnapClass::Multiple
        } else {
            SnapClass::Polyrhythm
        }
    }
}

/// Rhythmic classification of a snap ratio.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum SnapClass {
    /// Silence / zero interval.
    Rest,
    /// Quarter note / basic beat.
    Beat,
    /// Half note.
    Half,
    /// Double-time.
    Double,
    /// Subdivision (dotted, triplet, etc.)
    Subdivision,
    /// Multiple bars / long values.
    Multiple,
    /// A polyrhythm not in the standard hierarchy.
    Polyrhythm,
}

impl fmt::Display for SnapClass {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            SnapClass::Rest => write!(f, "Rest"),
            SnapClass::Beat => write!(f, "Beat"),
            SnapClass::Half => write!(f, "Half"),
            SnapClass::Double => write!(f, "Double"),
            SnapClass::Subdivision => write!(f, "Subdivision"),
            SnapClass::Multiple => write!(f, "Multiple"),
            SnapClass::Polyrhythm => write!(f, "Polyrhythm"),
        }
    }
}

// ---------------------------------------------------------------------------
// Eisenstein lattice utilities
// ---------------------------------------------------------------------------

/// Test whether a rhythmic deviation snaps to a standard ratio within the
/// Eisenstein covering radius (1/√3).
#[inline]
pub fn within_covering_radius(deviation: f64) -> bool {
    deviation <= INV_SQRT_3
}

/// Best standard SnapRatio for a given BPM-relative beat fraction.
///
/// Searches fraction denominators up to `max_denom` and returns the closest
/// standard ratio that snaps.
pub fn best_snap(bpm_fraction: f64, max_denom: u32) -> Option<SnapRatio> {
    let standard_ratios = [
        SnapRatio::new(0, 1),   // rest
        SnapRatio::new(1, 4),   // sixteenth
        SnapRatio::new(1, 3),   // triplet
        SnapRatio::new(1, 2),   // eighth
        SnapRatio::new(3, 4),   // dotted eighth
        SnapRatio::new(1, 1),   // quarter
        SnapRatio::new(3, 2),   // dotted quarter
        SnapRatio::new(2, 1),   // half
        SnapRatio::new(3, 1),   // dotted half
        SnapRatio::new(4, 1),   // whole
    ];

    let target = SnapRatio::new(
        (bpm_fraction * max_denom as f64).round() as u32,
        max_denom,
    );

    // Among all standard ratios (excluding rest), find the closest one that snaps.
    let mut best: Option<SnapRatio> = None;
    let mut best_diff: f64 = f64::MAX;
    for &sr in &standard_ratios[1..] {
        if target.snaps_to(sr) {
            let diff = (sr.value() - bpm_fraction).abs();
            if diff < best_diff {
                best_diff = diff;
                best = Some(sr);
            }
        }
    }
    if let Some(sr) = best {
        return Some(sr);
    }
    // Only snap to rest if the target value is within the covering radius of 0
    if bpm_fraction.abs() < INV_SQRT_3 {
        return Some(standard_ratios[0]);
    }

    // Fallback: find closest standard ratio even if it doesn't snap
    standard_ratios
        .iter()
        .min_by(|a, b| {
            (a.value() - bpm_fraction)
                .abs()
                .partial_cmp(&(b.value() - bpm_fraction).abs())
                .unwrap_or(Ordering::Equal)
        })
        .copied()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_flux_channel_new() {
        let ch = FluxChannel::new(64);
        assert_eq!(ch.intensity, 64);
        assert_eq!(ch.cluster, None);
    }

    #[test]
    fn test_flux_channel_with_cluster() {
        let ch = FluxChannel::with_cluster(100, 2);
        assert_eq!(ch.intensity, 100);
        assert_eq!(ch.cluster, Some(2));
    }

    #[test]
    fn test_flux_channel_magnitude() {
        assert_eq!(FluxChannel::new(50).magnitude(), 50);
        assert_eq!(FluxChannel::new(-50).magnitude(), 50);
    }

    #[test]
    fn test_flux_channel_normalized() {
        let ch = FluxChannel::new(0);
        assert!((ch.normalized() - 128.0 / 255.0).abs() < 1e-10);
    }

    #[test]
    fn test_flux_vector_energy() {
        let v = FluxVector::uniform(100);
        // 9 channels * 100^2 = 90,000
        assert_eq!(v.energy(), 90000);
    }

    #[test]
    fn test_flux_vector_l2_distance() {
        let a = FluxVector::uniform(0);
        let b = FluxVector::uniform(10);
        let dist = a.l2_distance(&b);
        // sqrt(9 * 100) = sqrt(900) = 30.0
        assert!((dist - 30.0).abs() < 1e-10);
    }

    #[test]
    fn test_flux_vector_chebyshev() {
        let a = FluxVector::uniform(0);
        let b = FluxVector::uniform(127);
        assert_eq!(a.chebyshev_distance(&b), 127);
    }

    #[test]
    fn test_flux_vector_dot() {
        let a = FluxVector::uniform(10);
        let b = FluxVector::uniform(5);
        // 9 * 10 * 5 = 450
        assert_eq!(a.dot(&b), 450);
    }

    #[test]
    fn test_flux_vector_scale() {
        let a = FluxVector::uniform(100);
        let b = a.scale(0.5);
        for ch in &b.channels {
            assert_eq!(ch.intensity, 50);
        }
    }

    #[test]
    fn test_flux_vector_cluster_channels() {
        let mut chs = [FluxChannel::new(0); 9];
        chs[0] = FluxChannel::with_cluster(64, 1);
        chs[1] = FluxChannel::with_cluster(32, 1);
        chs[2] = FluxChannel::with_cluster(16, 2);
        let v = FluxVector::new(chs);
        let cluster1 = v.cluster_channels(1);
        assert_eq!(cluster1.len(), 2);
        let cluster2 = v.cluster_channels(2);
        assert_eq!(cluster2.len(), 1);
    }

    #[test]
    fn test_tzero_clock_default() {
        let clock = TZeroClock::default();
        assert!((clock.alpha - 0.1).abs() < 1e-10);
        assert_eq!(clock.n_ticks, 0);
    }

    #[test]
    fn test_tzero_clock_record() {
        let mut clock = TZeroClock::new(0.5);
        let ema1 = clock.record(10.0);
        assert!((ema1 - 10.0).abs() < 1e-10);
        let ema2 = clock.record(0.0);
        // 0.5 * 0.0 + 0.5 * 10.0 = 5.0
        assert!((ema2 - 5.0).abs() < 1e-10);
    }

    #[test]
    fn test_tzero_clock_half_life() {
        let clock = TZeroClock::with_half_life(10.0);
        assert!(clock.alpha > 0.0 && clock.alpha < 1.0);
        assert!((1.0 - clock.alpha).powi(10) < 0.51); // ~half-life check
    }

    #[test]
    fn test_tzero_clock_deviation() {
        let mut clock = TZeroClock::new(0.5);
        clock.record(100.0);
        clock.record(50.0);
        // tick=50, ema=75, deviation=-25
        assert!((clock.deviation() - (-25.0)).abs() < 1e-10);
    }

    #[test]
    fn test_room_musician_new() {
        let m = RoomMusician::new("Plato", 0);
        assert_eq!(m.name, "Plato");
        assert_eq!(m.channel, 0);
        assert!(!m.active);
    }

    #[test]
    fn test_room_musician_receive_midi() {
        let mut m = RoomMusician::new("Test", 4);
        let event = MidiEvent::note_on(64, 100);
        m.receive_midi(&event, 1.0);
        assert_eq!(m.target, 100);
        assert!(m.active);
        assert_eq!(m.clock.n_ticks, 1);
    }

    #[test]
    fn test_room_musician_express_into() {
        let mut m = RoomMusician::new("Bass", 3);
        m.target = 80;
        let mut flux = FluxVector::uniform(0);
        m.express_into(&mut flux);
        assert_eq!(flux.channels[3].intensity, 80);
    }

    #[test]
    fn test_snap_ratio_basics() {
        let sr = SnapRatio::new(1, 2);
        assert_eq!(sr.p, 1);
        assert_eq!(sr.q, 2);
        assert!((sr.value() - 0.5).abs() < 1e-10);
    }

    #[test]
    fn test_snap_ratio_classify() {
        assert_eq!(SnapRatio::new(0, 1).classify(), SnapClass::Rest);
        assert_eq!(SnapRatio::new(1, 1).classify(), SnapClass::Beat);
        assert_eq!(SnapRatio::new(1, 2).classify(), SnapClass::Half);
        assert_eq!(SnapRatio::new(2, 1).classify(), SnapClass::Double);
        assert_eq!(SnapRatio::new(1, 4).classify(), SnapClass::Subdivision);
        assert_eq!(SnapRatio::new(4, 1).classify(), SnapClass::Multiple);
    }

    #[test]
    fn test_best_snap() {
        // 0.5 should snap to 1/2
        let snap = best_snap(0.5, 16);
        assert!(snap.is_some());
        assert_eq!(snap.unwrap(), SnapRatio::new(1, 2));

        // Very close to 1/4
        let snap = best_snap(0.26, 32);
        assert!(snap.is_some());
        assert_eq!(snap.unwrap(), SnapRatio::new(1, 4));
    }

    #[test]
    fn test_within_covering_radius() {
        assert!(within_covering_radius(0.5));
        assert!(!within_covering_radius(1.0));
    }

    #[test]
    fn test_tzero_clock_momentum() {
        let mut clock = TZeroClock::new(0.5);
        let prior = clock.record(10.0);
        clock.record(20.0);
        let mom = clock.momentum(prior);
        assert!((mom - (15.0 - 10.0)).abs() < 1e-10);
    }

    #[test]
    fn test_tzero_clock_reset() {
        let mut clock = TZeroClock::new(0.5);
        clock.record(42.0);
        clock.reset();
        assert_eq!(clock.n_ticks, 0);
        assert_eq!(clock.tick, 0.0);
    }
}

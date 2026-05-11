/// Nod signal — a positive acknowledgment side-channel.
///
/// In PLATO rooms, a Nod communicates approval, agreement, or
/// "continue playing / I like what I hear" without MIDI data.

/// A Nod side-channel signal.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct Nod {
    /// The note or channel reference.
    pub note: i16,
    /// Intensity of the nod (0–127).
    pub intensity: i16,
    /// Whether this is an enthusiastic nod (>96 intensity).
    pub enthusiastic: bool,
}

impl Nod {
    /// Create a new Nod signal.
    #[inline]
    pub fn new(note: i16, intensity: i16) -> Self {
        let intensity = intensity.clamp(0, 127);
        Nod {
            note,
            intensity,
            enthusiastic: intensity > 96,
        }
    }

    /// Create a Nod from a MIDI note-on event velocity.
    #[inline]
    pub fn from_midi_velocity(note: u8, velocity: u8) -> Self {
        Nod::new(note as i16, velocity as i16)
    }

    /// Normalized intensity in [0.0, 1.0].
    #[inline]
    pub fn normalized(self) -> f64 {
        self.intensity as f64 / 127.0
    }

    /// Confidence level: basic nod vs enthusiastic nod.
    #[inline]
    pub fn confidence(self) -> f64 {
        if self.enthusiastic {
            1.0
        } else {
            0.5 + self.normalized() * 0.5
        }
    }
}

impl core::fmt::Display for Nod {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        write!(
            f,
            "Nod(note={} intensity={} {})",
            self.note,
            self.intensity,
            if self.enthusiastic { "✨" } else { "" }
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_nod_new() {
        let n = Nod::new(60, 80);
        assert_eq!(n.note, 60);
        assert_eq!(n.intensity, 80);
        assert!(!n.enthusiastic);
    }

    #[test]
    fn test_nod_enthusiastic() {
        let n = Nod::new(60, 120);
        assert!(n.enthusiastic);
    }

    #[test]
    fn test_nod_from_midi() {
        let n = Nod::from_midi_velocity(64, 127);
        assert_eq!(n.note, 64);
        assert_eq!(n.intensity, 127);
        assert!(n.enthusiastic);
    }

    #[test]
    fn test_nod_clamp() {
        let n = Nod::new(60, 200);
        assert_eq!(n.intensity, 127);
    }

    #[test]
    fn test_nod_normalized() {
        let n = Nod::new(60, 64);
        assert!((n.normalized() - 64.0 / 127.0).abs() < 1e-6);
    }

    #[test]
    fn test_nod_confidence() {
        let basic = Nod::new(60, 64);
        let enth = Nod::new(60, 127);
        assert!(basic.confidence() < 1.0);
        assert!((enth.confidence() - 1.0).abs() < 1e-6);
    }
}

/// Frown signal — a negative/admonishing side-channel.
///
/// In PLATO rooms, a Frown communicates disapproval, confusion, or
/// "that was wrong / stop doing that" without MIDI data interruption.

/// A Frown side-channel signal.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct Frown {
    /// The note or element that caused the frown.
    pub note: i16,
    /// Displeasure intensity (0–127).
    pub displeasure: i16,
    /// Whether this is a strong frown (>96 displeasure).
    pub strong: bool,
}

impl Frown {
    /// Create a new Frown signal.
    #[inline]
    pub fn new(note: i16, displeasure: i16) -> Self {
        let displeasure = displeasure.clamp(0, 127);
        Frown {
            note,
            displeasure,
            strong: displeasure > 96,
        }
    }

    /// Create a Frown from a MIDI note-off event.
    #[inline]
    pub fn from_midi_note_off(note: u8, velocity: u8) -> Self {
        Frown::new(note as i16, velocity as i16)
    }

    /// Normalized displeasure in [0.0, 1.0].
    #[inline]
    pub fn normalized(self) -> f64 {
        self.displeasure as f64 / 127.0
    }

    /// Convert to a negative importance weight for harmonic adjustments.
    #[inline]
    pub fn weight(self) -> f64 {
        -self.normalized()
    }
}

impl core::fmt::Display for Frown {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        write!(
            f,
            "Frown(note={} displeasure={} {})",
            self.note,
            self.displeasure,
            if self.strong { "😠" } else { "" }
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_frown_new() {
        let f = Frown::new(60, 30);
        assert_eq!(f.note, 60);
        assert_eq!(f.displeasure, 30);
        assert!(!f.strong);
    }

    #[test]
    fn test_frown_strong() {
        let f = Frown::new(60, 110);
        assert!(f.strong);
    }

    #[test]
    fn test_frown_from_note_off() {
        let f = Frown::from_midi_note_off(64, 50);
        assert_eq!(f.note, 64);
        assert_eq!(f.displeasure, 50);
    }

    #[test]
    fn test_frown_clamp() {
        let f = Frown::new(60, 200);
        assert_eq!(f.displeasure, 127);
    }

    #[test]
    fn test_frown_weight_negative() {
        let f = Frown::new(60, 64);
        assert!(f.weight() < 0.0);
    }
}

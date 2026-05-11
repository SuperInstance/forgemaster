/// Smile signal — a positive/playful side-channel.
///
/// In PLATO rooms, a Smile communicates delight, amusement, or
/// "that was clever / unexpected" without words.

/// A Smile side-channel signal.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct Smile {
    /// The element that caused the smile (controller/note ref).
    pub source: i16,
    /// Warmth/amplitude of the smile (0–127).
    pub warmth: i16,
    /// Whether this is a broad smile (>96 warmth).
    pub broad: bool,
}

impl Smile {
    /// Create a new Smile signal.
    #[inline]
    pub fn new(source: i16, warmth: i16) -> Self {
        let warmth = warmth.clamp(0, 127);
        Smile {
            source,
            warmth,
            broad: warmth > 96,
        }
    }

    /// Create a Smile from a MIDI CC value (0–127).
    #[inline]
    pub fn from_cc(controller: u8, value: u8) -> Self {
        Smile::new(controller as i16, value as i16)
    }

    /// Normalized warmth in [0.0, 1.0].
    #[inline]
    pub fn normalized(self) -> f64 {
        self.warmth as f64 / 127.0
    }
}

impl core::fmt::Display for Smile {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        write!(
            f,
            "Smile(source={} warmth={} {})",
            self.source,
            self.warmth,
            if self.broad { "😊" } else { "" }
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_smile_new() {
        let s = Smile::new(7, 64);
        assert_eq!(s.source, 7);
        assert_eq!(s.warmth, 64);
        assert!(!s.broad);
    }

    #[test]
    fn test_smile_broad() {
        let s = Smile::new(7, 100);
        assert!(s.broad);
    }

    #[test]
    fn test_smile_from_cc() {
        let s = Smile::from_cc(10, 127);
        assert_eq!(s.source, 10);
        assert_eq!(s.warmth, 127);
    }

    #[test]
    fn test_smile_clamp() {
        let s = Smile::new(7, 200);
        assert_eq!(s.warmth, 127);
    }

    #[test]
    fn test_smile_normalized() {
        let s = Smile::new(7, 64);
        assert!((s.normalized() - 64.0 / 127.0).abs() < 1e-6);
    }
}

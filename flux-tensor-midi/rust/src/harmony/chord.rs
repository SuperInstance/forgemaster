/// Chord quality analysis from flux vector harmonic profiles.
///
/// Maps the 9 flux channels into pitch-class sets and identifies
/// common chord qualities: major, minor, diminished, augmented, etc.

/// Chord quality enumeration for harmonic analysis.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ChordQuality {
    /// Root only — no chord.
    Root,
    /// Major triad: root, major third, perfect fifth.
    Major,
    /// Minor triad: root, minor third, perfect fifth.
    Minor,
    /// Diminished: root, minor third, diminished fifth.
    Diminished,
    /// Augmented: root, major third, augmented fifth.
    Augmented,
    /// Dominant seventh: major triad + minor seventh.
    Dominant7,
    /// Major seventh: major triad + major seventh.
    Major7,
    /// Minor seventh: minor triad + minor seventh.
    Minor7,
    /// Suspended fourth: root, perfect fourth, perfect fifth.
    Sus4,
    /// Suspended second: root, major second, perfect fifth.
    Sus2,
    /// Power chord: root, perfect fifth only.
    Power,
    /// Not a recognized chord.
    NoChord,
}

impl ChordQuality {
    /// Determine chord quality from a set of active flux channels.
    ///
    /// Channels 0-8 represent chromatic pitches starting from a root.
    /// Channels are mapped: C=0, C#=1, D=2, etc.
    /// The root is assumed at channel 0.
    pub fn from_active_channels(active: &[usize]) -> Self {
        let set: Vec<usize> = {
            let mut v = active.to_vec();
            v.sort_unstable();
            v.dedup();
            v
        };

        if set.is_empty() {
            return ChordQuality::Root;
        }

        let has = |n: usize| set.contains(&(n % 12));

        match set.len() {
            1 => ChordQuality::Root,
            2 => {
                // Check for power chord: root + fifth
                if has(0) && has(7) {
                    ChordQuality::Power
                } else {
                    ChordQuality::NoChord
                }
            }
            _ => {
                if has(0) {
                    let has_minor_third = has(3);
                    let has_major_third = has(4);
                    let has_fifth = has(7);
                    let has_flat_fifth = has(6);
                    let has_sharp_fifth = has(8);
                    let has_seventh = has(10);
                    let has_major_seventh = has(11);
                    let has_sus4 = has(5);
                    let has_sus2 = has(2);

                    // Seventh chords
                    if has_major_third && has_fifth && has_seventh {
                        return ChordQuality::Dominant7;
                    }
                    if has_major_third && has_fifth && has_major_seventh {
                        return ChordQuality::Major7;
                    }
                    if has_minor_third && has_fifth && has_seventh {
                        return ChordQuality::Minor7;
                    }

                    // Suspended chords (check before triads)
                    if has_sus4 && has_fifth && !has_minor_third && !has_major_third {
                        return ChordQuality::Sus4;
                    }
                    if has_sus2 && has_fifth && !has_minor_third && !has_major_third {
                        return ChordQuality::Sus2;
                    }

                    // Triads
                    if has_major_third && has_fifth {
                        return ChordQuality::Major;
                    }
                    if has_minor_third && has_fifth {
                        return ChordQuality::Minor;
                    }
                    if has_minor_third && has_flat_fifth {
                        return ChordQuality::Diminished;
                    }
                    if has_major_third && has_sharp_fifth {
                        return ChordQuality::Augmented;
                    }
                }

                ChordQuality::NoChord
            }
        }
    }

    /// Confidence in the chord quality detection (0.0–1.0).
    pub fn confidence(self, active_count: usize) -> f64 {
        match self {
            ChordQuality::Root => 1.0,
            ChordQuality::NoChord => 0.0,
            quality => {
                // More active channels = more data = higher confidence
                (active_count as f64).min(9.0) / 9.0
            }
        }
    }
}

impl core::fmt::Display for ChordQuality {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        match self {
            ChordQuality::Root => write!(f, "Root"),
            ChordQuality::Major => write!(f, "Major"),
            ChordQuality::Minor => write!(f, "Minor"),
            ChordQuality::Diminished => write!(f, "Dim"),
            ChordQuality::Augmented => write!(f, "Aug"),
            ChordQuality::Dominant7 => write!(f, "Dom7"),
            ChordQuality::Major7 => write!(f, "Maj7"),
            ChordQuality::Minor7 => write!(f, "Min7"),
            ChordQuality::Sus4 => write!(f, "Sus4"),
            ChordQuality::Sus2 => write!(f, "Sus2"),
            ChordQuality::Power => write!(f, "Power"),
            ChordQuality::NoChord => write!(f, "N/C"),
        }
    }
}

/// Harmony state: the current chord quality and its context.
#[derive(Debug, Clone)]
pub struct HarmonyState {
    /// Current chord quality.
    pub quality: ChordQuality,
    /// Active flux channel indices contributing to the harmony.
    pub active_channels: Vec<usize>,
    /// Number of samples contributing to this state.
    pub stability_counter: u32,
    /// Confidence in the detection.
    pub confidence: f64,
}

impl HarmonyState {
    /// Create a new HarmonyState from a set of active channel indices.
    pub fn new(active_channels: &[usize]) -> Self {
        let quality = ChordQuality::from_active_channels(active_channels);
        let confidence = quality.confidence(active_channels.len());
        HarmonyState {
            quality,
            active_channels: active_channels.to_vec(),
            stability_counter: 0,
            confidence,
        }
    }

    /// Update harmony state with new active channels.
    pub fn update(&mut self, active_channels: &[usize]) {
        let new_quality = ChordQuality::from_active_channels(active_channels);

        if new_quality == self.quality {
            self.stability_counter += 1;
        } else {
            self.quality = new_quality;
            self.stability_counter = 0;
        }

        self.active_channels = active_channels.to_vec();
        self.confidence = self.quality.confidence(self.active_channels.len());
    }

    /// Whether the harmony has converged (stable for N+ updates).
    #[inline]
    pub fn is_stable(&self, threshold: u32) -> bool {
        self.stability_counter >= threshold
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_chord_quality_major() {
        // C major: C(0), E(4), G(7)
        let active = vec![0, 4, 7];
        assert_eq!(ChordQuality::from_active_channels(&active), ChordQuality::Major);
    }

    #[test]
    fn test_chord_quality_minor() {
        // C minor: C(0), Eb(3), G(7)
        let active = vec![0, 3, 7];
        assert_eq!(ChordQuality::from_active_channels(&active), ChordQuality::Minor);
    }

    #[test]
    fn test_chord_quality_diminished() {
        // C dim: C(0), Eb(3), Gb(6)
        let active = vec![0, 3, 6];
        assert_eq!(ChordQuality::from_active_channels(&active), ChordQuality::Diminished);
    }

    #[test]
    fn test_chord_quality_augmented() {
        // C aug: C(0), E(4), G#(8)
        let active = vec![0, 4, 8];
        assert_eq!(ChordQuality::from_active_channels(&active), ChordQuality::Augmented);
    }

    #[test]
    fn test_chord_quality_dominant7() {
        // C7: C(0), E(4), G(7), Bb(10)
        let active = vec![0, 4, 7, 10];
        assert_eq!(ChordQuality::from_active_channels(&active), ChordQuality::Dominant7);
    }

    #[test]
    fn test_chord_quality_major7() {
        // Cmaj7: C(0), E(4), G(7), B(11)
        let active = vec![0, 4, 7, 11];
        assert_eq!(ChordQuality::from_active_channels(&active), ChordQuality::Major7);
    }

    #[test]
    fn test_chord_quality_minor7() {
        // Cm7: C(0), Eb(3), G(7), Bb(10)
        let active = vec![0, 3, 7, 10];
        assert_eq!(ChordQuality::from_active_channels(&active), ChordQuality::Minor7);
    }

    #[test]
    fn test_chord_quality_sus4() {
        let active = vec![0, 5, 7];
        assert_eq!(ChordQuality::from_active_channels(&active), ChordQuality::Sus4);
    }

    #[test]
    fn test_chord_quality_sus2() {
        let active = vec![0, 2, 7];
        assert_eq!(ChordQuality::from_active_channels(&active), ChordQuality::Sus2);
    }

    #[test]
    fn test_chord_quality_power() {
        let active = vec![0, 7];
        assert_eq!(ChordQuality::from_active_channels(&active), ChordQuality::Power);
    }

    #[test]
    fn test_chord_quality_root() {
        let active = vec![0];
        assert_eq!(ChordQuality::from_active_channels(&active), ChordQuality::Root);
    }

    #[test]
    fn test_harmony_state_new() {
        let state = HarmonyState::new(&[0, 4, 7]);
        assert_eq!(state.quality, ChordQuality::Major);
        assert_eq!(state.stability_counter, 0);
    }

    #[test]
    fn test_harmony_state_update_same() {
        let mut state = HarmonyState::new(&[0, 4, 7]);
        state.update(&[0, 4, 7]);
        assert_eq!(state.stability_counter, 1);
        assert!(state.is_stable(1));
    }

    #[test]
    fn test_harmony_state_update_change() {
        let mut state = HarmonyState::new(&[0, 4, 7]); // Major
        assert_eq!(state.stability_counter, 0);
        state.update(&[0, 3, 7]); // Minor
        assert_eq!(state.quality, ChordQuality::Minor);
        assert_eq!(state.stability_counter, 0);
    }
}

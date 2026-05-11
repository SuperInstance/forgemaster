/// Score — a musical score for a band, built from MIDI events and snap timing.
///
/// A Score represents a sequence of musical events with snap-classified
/// rhythmic positions.

use crate::core::SnapClass;
use crate::ensemble::band::Band;
use crate::MidiEvent;

/// A single scored event in the score.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct ScoredEvent {
    /// The MIDI event.
    pub event: MidiEvent,
    /// Beat position (quarter notes from start).
    pub beat: f64,
    /// Duration in beats.
    pub duration: f64,
    /// Rhythmic snap class.
    pub snap: SnapClass,
    /// Intensity (0.0–1.0).
    pub intensity: f64,
}

impl ScoredEvent {
    /// Create a new ScoredEvent.
    pub fn new(event: MidiEvent, beat: f64, duration: f64, snap: SnapClass) -> Self {
        let intensity = event.velocity as f64 / 127.0;
        ScoredEvent {
            event,
            beat,
            duration,
            snap,
            intensity,
        }
    }
}

/// A complete musical score for a band.
#[derive(Debug, Clone)]
pub struct Score {
    /// Name of the score / piece.
    pub name: String,
    /// Target band for this score.
    pub band_name: String,
    /// All events in order.
    pub events: Vec<ScoredEvent>,
    /// Total duration in beats.
    pub total_beats: f64,
    /// Tempo in BPM.
    pub tempo: f64,
}

impl Score {
    /// Create a new empty score.
    #[inline]
    pub fn new(name: &str, band_name: &str, tempo: f64) -> Self {
        Score {
            name: name.to_string(),
            band_name: band_name.to_string(),
            events: Vec::new(),
            total_beats: 0.0,
            tempo,
        }
    }

    /// Create a score from a sequence of MIDI events with timing.
    ///
    /// `position_beats` is parallel to `events` — the beat position of each event.
    /// `durations` is optional durations for each event.
    pub fn from_events(
        name: &str,
        band_name: &str,
        events: &[MidiEvent],
        position_beats: &[f64],
        durations: Option<&[f64]>,
        tempo: f64,
    ) -> Self {
        let mut scored = Vec::with_capacity(events.len());
        let dur_default = 0.25; // sixteenth note default
        let mut max_beat = 0.0;

        for (i, event) in events.iter().enumerate() {
            let beat = position_beats.get(i).copied().unwrap_or(0.0);
            let duration = durations
                .and_then(|d| d.get(i))
                .copied()
                .unwrap_or(dur_default);
            let snap_class = crate::core::best_snap(duration, 16)
                .map(|sr| sr.classify())
                .unwrap_or(SnapClass::Subdivision);

            scored.push(ScoredEvent::new(*event, beat, duration, snap_class));
            max_beat = max_beat.max(beat + duration);
        }

        Score {
            name: name.to_string(),
            band_name: band_name.to_string(),
            events: scored,
            total_beats: max_beat,
            tempo,
        }
    }

    /// Add a single event to the score.
    pub fn add_event(&mut self, event: ScoredEvent) {
        let end = event.beat + event.duration;
        if end > self.total_beats {
            self.total_beats = end;
        }
        self.events.push(event);
    }

    /// Events at a given beat position within a tolerance.
    pub fn events_at_beat(&self, beat: f64, tolerance: f64) -> Vec<&ScoredEvent> {
        self.events
            .iter()
            .filter(|e| (e.beat - beat).abs() <= tolerance)
            .collect()
    }

    /// Total duration in seconds.
    #[inline]
    pub fn duration_seconds(&self) -> f64 {
        self.total_beats / (self.tempo / 60.0)
    }

    /// Number of events in the score.
    #[inline]
    pub fn event_count(&self) -> usize {
        self.events.len()
    }

    /// Play the score through a band, returning the final band state.
    pub fn play_through(&self, band: &mut Band, start_time: f64) {
        for scored in &self.events {
            let now = start_time + scored.beat * (60.0 / self.tempo);
            band.play_midi(&scored.event, now);
        }
    }

    /// Merge another score into this one.
    pub fn merge(&mut self, other: &Score) {
        for event in &other.events {
            self.add_event(*event);
        }
        if self.tempo != other.tempo {
            // Take the average tempo on merge
            self.tempo = (self.tempo + other.tempo) / 2.0;
        }
    }
}

impl core::fmt::Display for Score {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        write!(
            f,
            "Score '{}' for '{}' ({} events, {:.1} beats @ {:.0} BPM)",
            self.name,
            self.band_name,
            self.events.len(),
            self.total_beats,
            self.tempo
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_score_new() {
        let score = Score::new("Test", "Band", 120.0);
        assert_eq!(score.name, "Test");
        assert_eq!(score.event_count(), 0);
    }

    #[test]
    fn test_score_from_events() {
        let events = vec![
            MidiEvent::note_on(60, 100),
            MidiEvent::note_on(64, 80),
            MidiEvent::note_on(67, 90),
        ];
        let beats = vec![0.0, 1.0, 2.0];
        let score = Score::from_events("CMajor", "Band", &events, &beats, None, 120.0);
        assert_eq!(score.event_count(), 3);
        assert_eq!(score.tempo as u32, 120);
    }

    #[test]
    fn test_score_add_event() {
        let mut score = Score::new("Piece", "Band", 120.0);
        let se = ScoredEvent::new(MidiEvent::note_on(60, 100), 0.0, 0.5, SnapClass::Half);
        score.add_event(se);
        assert_eq!(score.event_count(), 1);
        assert_eq!(score.total_beats, 0.5);
    }

    #[test]
    fn test_score_events_at_beat() {
        let mut score = Score::new("Test", "Band", 120.0);
        score.add_event(ScoredEvent::new(
            MidiEvent::note_on(60, 100),
            0.0,
            0.25,
            SnapClass::Beat,
        ));
        score.add_event(ScoredEvent::new(
            MidiEvent::note_on(64, 80),
            1.0,
            0.25,
            SnapClass::Beat,
        ));
        let at_one = score.events_at_beat(1.0, 0.01);
        assert_eq!(at_one.len(), 1);
        assert_eq!(at_one[0].event.data1, 64);
    }

    #[test]
    fn test_score_duration_seconds() {
        let mut score = Score::new("Test", "Band", 120.0);
        score.total_beats = 4.0; // one measure of 4/4
        let secs = score.duration_seconds();
        // 4 beats at 120 BPM = 2 seconds
        assert!((secs - 2.0).abs() < 1e-6);
    }

    #[test]
    fn test_score_play_through() {
        let mut band = Band::with_musicians("Room", &["M1", "M2"]);
        let events = vec![
            MidiEvent::note_on(60, 100),
            MidiEvent::note_on(64, 80),
        ];
        let beats = vec![0.0, 1.0];
        let score = Score::from_events("Test", "Room", &events, &beats, None, 120.0);
        score.play_through(&mut band, 0.0);
        assert!(band.energy() > 0);
    }

    #[test]
    fn test_score_merge() {
        let mut score1 = Score::new("A", "Band", 120.0);
        score1.add_event(ScoredEvent::new(
            MidiEvent::note_on(60, 100),
            0.0,
            1.0,
            SnapClass::Beat,
        ));

        let mut score2 = Score::new("B", "Band", 140.0);
        score2.add_event(ScoredEvent::new(
            MidiEvent::note_on(64, 80),
            2.0,
            1.0,
            SnapClass::Beat,
        ));

        score1.merge(&score2);
        assert_eq!(score1.event_count(), 2);
        assert!((score1.tempo - 130.0).abs() < 1e-6); // average tempo
    }

    #[test]
    fn test_scored_event_snap() {
        let se = ScoredEvent::new(MidiEvent::note_on(60, 100), 0.0, 1.0, SnapClass::Beat);
        assert_eq!(se.snap, SnapClass::Beat);
        assert_eq!(se.intensity, 100.0 / 127.0);
    }
}

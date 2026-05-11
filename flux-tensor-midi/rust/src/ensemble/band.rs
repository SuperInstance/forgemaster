/// Band — an ensemble of musicians playing together in a PLATO room.
///
/// A Band manages up to 9 musicians, their flux vectors, T-0 clocks,
/// and provides collective operations: energy, harmony, timing.

use crate::core::{FluxChannel, FluxVector, RoomMusician, TZeroClock};
use crate::harmony::chord::{ChordQuality, HarmonyState};
use crate::harmony::jaccard;
use crate::MidiEvent;

/// Maximum number of musicians in a band (same as flux channels).
pub const MAX_MUSICIANS: usize = 9;

/// A band of musicians playing in a PLATO room.
#[derive(Debug, Clone)]
pub struct Band {
    /// Name of the band / room.
    pub name: String,
    /// The musicians in the band (index = flux channel).
    pub musicians: Vec<RoomMusician>,
    /// The band's T-0 clock for collective timing.
    pub clock: TZeroClock,
    /// Current flux vector state.
    pub flux: FluxVector,
    /// Current harmony state.
    pub harmony: HarmonyState,
    /// Previous flux vector for delta computation.
    pub previous_flux: Option<FluxVector>,
}

impl Band {
    /// Create a new empty band.
    #[inline]
    pub fn new(name: &str) -> Self {
        Band {
            name: name.to_string(),
            musicians: Vec::with_capacity(MAX_MUSICIANS),
            clock: TZeroClock::default(),
            flux: FluxVector::uniform(0),
            harmony: HarmonyState::new(&[]),
            previous_flux: None,
        }
    }

    /// Create a band pre-populated with named musicians.
    pub fn with_musicians(name: &str, names: &[&str]) -> Self {
        let count = names.len().min(MAX_MUSICIANS);
        let musicians: Vec<RoomMusician> = names[..count]
            .iter()
            .enumerate()
            .map(|(i, n)| RoomMusician::new(n, i))
            .collect();

        Band {
            name: name.to_string(),
            musicians,
            clock: TZeroClock::default(),
            flux: FluxVector::uniform(0),
            harmony: HarmonyState::new(&[]),
            previous_flux: None,
        }
    }

    /// Add a musician to the band. Returns an error if the band is full.
    pub fn add_musician(&mut self, musician: RoomMusician) -> Result<(), &'static str> {
        if self.musicians.len() >= MAX_MUSICIANS {
            return Err("Band is full (max 9 musicians)");
        }
        if musician.channel != self.musicians.len() {
            return Err("Musician channel must match next available index");
        }
        self.musicians.push(musician);
        Ok(())
    }

    /// Remove the last musician from the band.
    #[inline]
    pub fn remove_musician(&mut self) -> Option<RoomMusician> {
        self.musicians.pop()
    }

    /// Number of musicians in the band.
    #[inline]
    pub fn musician_count(&self) -> usize {
        self.musicians.len()
    }

    /// Send a MIDI event to the band, updating the relevant musician.
    pub fn play_midi(&mut self, event: &MidiEvent, now: f64) {
        // Save current flux as previous before updating (only after first event)
        if self.clock.n_ticks > 0 {
            self.previous_flux = Some(self.flux);
        }
        self.clock.tick(now);

        // Map MIDI channel to flux channel
        let flux_ch = crate::midi::channel::midi_to_flux_channel(event.channel());

        // Find the musician at that flux channel, or update flux directly
        if let Some(musician) = self
            .musicians
            .iter_mut()
            .find(|m| m.channel == flux_ch)
        {
            musician.receive_midi(event, now);
            musician.express_into(&mut self.flux);
        } else {
            // Direct flux update if no musician assigned
            let vel = event.velocity;
            self.flux.channels[flux_ch] = crate::core::FluxChannel::new(vel as i8);
        }

        // Update harmony analysis
        let active: Vec<usize> = self
            .flux
            .channels
            .iter()
            .enumerate()
            .filter(|(_, ch)| ch.intensity > 0)
            .map(|(i, _)| i)
            .collect();
        self.harmony.update(&active);
    }

    /// Total energy of the band right now.
    #[inline]
    pub fn energy(&self) -> u32 {
        self.flux.energy()
    }

    /// Jaccard similarity between current and previous flux.
    #[inline]
    pub fn flux_similarity(&self) -> Option<f64> {
        self.previous_flux
            .map(|prev| jaccard::jaccard_active(&prev, &self.flux))
    }

    /// Reset all musicians and flux to zero.
    pub fn reset(&mut self) {
        self.clock.reset();
        self.flux = FluxVector::uniform(0);
        self.previous_flux = None;
        self.harmony = HarmonyState::new(&[]);
        for musician in &mut self.musicians {
            musician.target = 0;
            musician.active = false;
            musician.clock.reset();
        }
    }

    /// Collect current flux channels for the band's active cluster.
    #[inline]
    pub fn cluster_flux(&self, cluster: u8) -> Vec<crate::core::FluxChannel> {
        self.flux.cluster_channels(cluster)
    }
}

impl core::fmt::Display for Band {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        write!(
            f,
            "Band '{}' ({} musicians, energy={}, harmony={})",
            self.name,
            self.musicians.len(),
            self.energy(),
            self.harmony.quality
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_band_new() {
        let band = Band::new("Test Room");
        assert_eq!(band.musicians.len(), 0);
        assert_eq!(band.name, "Test Room");
    }

    #[test]
    fn test_band_with_musicians() {
        let band = Band::with_musicians("Jazz Room", &["Piano", "Bass", "Drums"]);
        assert_eq!(band.musician_count(), 3);
        assert_eq!(band.musicians[0].name, "Piano");
        assert_eq!(band.musicians[1].name, "Bass");
        assert_eq!(band.musicians[2].name, "Drums");
    }

    #[test]
    fn test_band_add_musician() {
        let mut band = Band::new("Room");
        let m = RoomMusician::new("Guitar", 0);
        assert!(band.add_musician(m).is_ok());
        assert_eq!(band.musician_count(), 1);
    }

    #[test]
    fn test_band_remove_musician() {
        let mut band = Band::with_musicians("Room", &["A", "B"]);
        let removed = band.remove_musician();
        assert!(removed.is_some());
        assert_eq!(band.musician_count(), 1);
    }

    #[test]
    fn test_band_play_midi() {
        let mut band = Band::with_musicians("Room", &["Vox"]);
        let event = MidiEvent::note_on(60, 100);
        band.play_midi(&event, 1.0);
        assert!(band.energy() > 0);
        assert_eq!(band.harmony.quality, ChordQuality::Root);
    }

    #[test]
    fn test_band_energy() {
        let mut band = Band::with_musicians("Room", &["Bass"]);
        let event = MidiEvent::note_on(36, 127);
        band.play_midi(&event, 1.0);
        assert_eq!(band.energy(), 127 * 127); // 1 channel active
    }

    #[test]
    fn test_band_flux_similarity() {
        let mut band = Band::with_musicians("Room", &["Kick"]);
        let event = MidiEvent::note_on(36, 100);
        band.play_midi(&event, 1.0);
        // After first event, no previous flux yet
        assert!(band.flux_similarity().is_none());
        // Second event creates a previous
        let event2 = MidiEvent::note_on(36, 100);
        band.play_midi(&event2, 2.0);
        let sim = band.flux_similarity();
        assert!(sim.is_some());
        assert!((sim.unwrap() - 1.0).abs() < 1e-10);
    }

    #[test]
    fn test_band_reset() {
        let mut band = Band::with_musicians("Room", &["Pad"]);
        band.play_midi(&MidiEvent::note_on(48, 100), 1.0);
        band.reset();
        assert_eq!(band.energy(), 0);
        assert_eq!(band.musicians[0].target, 0);
    }

    #[test]
    fn test_band_full_error() {
        let mut band = Band::new("Room");
        for i in 0..9 {
            let m = RoomMusician::new(&format!("M{i}"), i);
            assert!(band.add_musician(m).is_ok());
        }
        // Band is full (9 musicians), adding another should fail
        // Use channel 8 since adding is already blocked by musician_count check
        let extra = RoomMusician::new("Overflow", 8);
        assert!(band.add_musician(extra).is_err());
    }

    #[test]
    fn test_band_harmony_update() {
        let mut band = Band::with_musicians("Room", &[]);
        // Direct flux manipulation via MIDI
        let c_major_notes = [(60, 100), (64, 100), (67, 100)];
        for (i, (note, vel)) in c_major_notes.iter().enumerate() {
            let event = MidiEvent::note_on(*note, *vel);
            band.play_midi(&event, i as f64 + 1.0);
        }
        assert_eq!(band.harmony.quality, ChordQuality::Root);
    }
}

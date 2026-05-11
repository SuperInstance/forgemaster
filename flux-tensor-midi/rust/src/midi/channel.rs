/// MIDI channel mapping and voice assignment.

/// 16 standard MIDI channels.
pub const MIDI_CHANNEL_COUNT: usize = 16;

/// Mapping from MIDI channels to flux channels (9 flux channels, 16 MIDI channels).
///
/// Channels 0-8 map 1:1 to flux channels 0-8.
/// Channels 9-15 collapse: percussion/flux channel 8.
pub fn midi_to_flux_channel(midi_ch: usize) -> usize {
    if midi_ch < 9 {
        midi_ch
    } else {
        8 // percussion and extras collapse to channel 8
    }
}

/// A MIDI channel configuration for a room.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct MidiChannelConfig {
    /// MIDI program number (instrument).
    pub program: u8,
    /// Volume (0–127).
    pub volume: u8,
    /// Pan (-64 = hard left, 0 = center, 63 = hard right).
    pub pan: i8,
    /// Whether the channel is muted.
    pub muted: bool,
}

impl MidiChannelConfig {
    /// Create a default MIDI channel config for the given program.
    #[inline]
    pub fn new(program: u8) -> Self {
        MidiChannelConfig {
            program,
            volume: 100,
            pan: 0,
            muted: false,
        }
    }

    /// Set the volume (clamped to 0–127).
    #[inline]
    pub fn set_volume(&mut self, vol: u8) {
        self.volume = vol.min(127);
    }

    /// Set the pan (clamped to -64..63).
    #[inline]
    pub fn set_pan(&mut self, pan: i8) {
        self.pan = pan.clamp(-64, 63);
    }

    /// Toggle mute state.
    #[inline]
    pub fn toggle_mute(&mut self) {
        self.muted = !self.muted;
    }

    /// The effective volume considering mute state.
    #[inline]
    pub fn effective_volume(&self) -> u8 {
        if self.muted {
            0
        } else {
            self.volume
        }
    }
}

impl Default for MidiChannelConfig {
    fn default() -> Self {
        MidiChannelConfig::new(0) // Acoustic Grand Piano
    }
}

/// A complete map from 16 MIDI channels to their configurations.
#[derive(Debug, Clone)]
pub struct MidiChannelMap {
    pub channels: [MidiChannelConfig; MIDI_CHANNEL_COUNT],
}

impl MidiChannelMap {
    /// Create a new channel map with all channels at default.
    #[inline]
    pub fn new() -> Self {
        MidiChannelMap {
            channels: [MidiChannelConfig::default(); MIDI_CHANNEL_COUNT],
        }
    }

    /// Get a mutable reference to a channel's config.
    #[inline]
    pub fn channel_mut(&mut self, ch: usize) -> Option<&mut MidiChannelConfig> {
        self.channels.get_mut(ch)
    }

    /// Get a channel's config.
    #[inline]
    pub fn channel(&self, ch: usize) -> Option<&MidiChannelConfig> {
        self.channels.get(ch)
    }

    /// Set program for a channel.
    #[inline]
    pub fn set_program(&mut self, ch: usize, program: u8) {
        if let Some(cfg) = self.channels.get_mut(ch) {
            cfg.program = program;
        }
    }

    /// Reset all channels to default.
    #[inline]
    pub fn reset(&mut self) {
        *self = MidiChannelMap::new();
    }
}

impl Default for MidiChannelMap {
    fn default() -> Self {
        MidiChannelMap::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_midi_to_flux_channel() {
        assert_eq!(midi_to_flux_channel(0), 0);
        assert_eq!(midi_to_flux_channel(5), 5);
        assert_eq!(midi_to_flux_channel(8), 8);
        assert_eq!(midi_to_flux_channel(9), 8); // percussion collapses
        assert_eq!(midi_to_flux_channel(15), 8);
    }

    #[test]
    fn test_channel_config_default() {
        let cfg = MidiChannelConfig::new(8); // Celesta
        assert_eq!(cfg.program, 8);
        assert_eq!(cfg.volume, 100);
        assert_eq!(cfg.pan, 0);
        assert!(!cfg.muted);
    }

    #[test]
    fn test_channel_config_volume_clamping() {
        let mut cfg = MidiChannelConfig::new(0);
        cfg.set_volume(200);
        assert_eq!(cfg.volume, 127);
        cfg.set_volume(0);
        assert_eq!(cfg.volume, 0);
    }

    #[test]
    fn test_channel_config_pan() {
        let mut cfg = MidiChannelConfig::new(0);
        cfg.set_pan(-100);
        assert_eq!(cfg.pan, -64);
        cfg.set_pan(100);
        assert_eq!(cfg.pan, 63);
    }

    #[test]
    fn test_channel_config_mute() {
        let mut cfg = MidiChannelConfig::new(0);
        cfg.toggle_mute();
        assert!(cfg.muted);
        assert_eq!(cfg.effective_volume(), 0);
        cfg.toggle_mute();
        assert!(!cfg.muted);
        assert_eq!(cfg.effective_volume(), 100);
    }

    #[test]
    fn test_channel_map() {
        let mut map = MidiChannelMap::new();
        assert!(!map.channel(0).unwrap().muted);
        map.set_program(0, 24); // Nylon Guitar
        assert_eq!(map.channel(0).unwrap().program, 24);
    }

    #[test]
    fn test_channel_map_reset() {
        let mut map = MidiChannelMap::new();
        map.set_program(5, 40);
        map.reset();
        assert_eq!(map.channel(5).unwrap().program, 0);
    }
}

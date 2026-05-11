/// MIDI event representation and construction.

use crate::{Frown, Nod, Smile};

/// A parsed MIDI event with semantic meaning for FLUX-Tensor-MIDI.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct MidiEvent {
    /// Status byte — the MIDI command/type.
    pub status: u8,
    /// First data byte (note number, controller, etc.).
    pub data1: u8,
    /// Second data byte (velocity, value, etc.).
    pub data2: u8,
    /// Derived velocity/intensity from the event.
    pub velocity: u8,
    /// Timestamp in ticks or milliseconds.
    pub timestamp: u64,
}

impl MidiEvent {
    /// Raw MIDI status constants.
    pub const NOTE_OFF: u8 = 0x80;
    pub const NOTE_ON: u8 = 0x90;
    pub const POLY_AFTERTOUCH: u8 = 0xA0;
    pub const CONTROL_CHANGE: u8 = 0xB0;
    pub const PROGRAM_CHANGE: u8 = 0xC0;
    pub const CHANNEL_AFTERTOUCH: u8 = 0xD0;
    pub const PITCH_BEND: u8 = 0xE0;

    /// Create a new midi event from raw bytes.
    #[inline]
    pub fn new(status: u8, data1: u8, data2: u8, timestamp: u64) -> Self {
        let velocity = if status & 0xF0 == Self::NOTE_ON {
            data2
        } else if status & 0xF0 == Self::NOTE_OFF {
            0
        } else if status & 0xF0 == Self::CONTROL_CHANGE {
            data2
        } else if status & 0xF0 == Self::POLY_AFTERTOUCH {
            data2
        } else {
            64 // default intensity for other events
        };

        MidiEvent {
            status,
            data1,
            data2,
            velocity,
            timestamp,
        }
    }

    /// Shortcut for a Note On event.
    #[inline]
    pub fn note_on(note: u8, velocity: u8) -> Self {
        MidiEvent::new(Self::NOTE_ON | 0, note, velocity, 0)
    }

    /// Shortcut for a Note Off event.
    #[inline]
    pub fn note_off(note: u8, velocity: u8) -> Self {
        MidiEvent::new(Self::NOTE_OFF | 0, note, velocity, 0)
    }

    /// Shortcut for a Control Change event.
    #[inline]
    pub fn control_change(controller: u8, value: u8) -> Self {
        MidiEvent::new(Self::CONTROL_CHANGE | 0, controller, value, 0)
    }

    /// Channel (0–15) extracted from the status byte.
    #[inline]
    pub fn channel(&self) -> usize {
        (self.status & 0x0F) as usize
    }

    /// MIDI command type (upper nibble).
    #[inline]
    pub fn command(&self) -> u8 {
        self.status & 0xF0
    }

    /// Whether this is a Note On with non-zero velocity.
    #[inline]
    pub fn is_note_on(&self) -> bool {
        self.command() == Self::NOTE_ON && self.data2 > 0
    }

    /// Whether this is a Note Off or a Note On with velocity=0.
    #[inline]
    pub fn is_note_off(&self) -> bool {
        self.command() == Self::NOTE_OFF || (self.command() == Self::NOTE_ON && self.data2 == 0)
    }

    /// Express this MIDI event as a Nod side-channel signal.
    pub fn to_nod(&self) -> Option<Nod> {
        if self.is_note_on() {
            Some(Nod::new(self.data1 as i16, self.velocity as i16))
        } else {
            None
        }
    }

    /// Express this MIDI event as a Smile side-channel signal.
    pub fn to_smile(&self) -> Option<Smile> {
        if self.command() == Self::CONTROL_CHANGE && self.data2 > 0 {
            Some(Smile::new(self.data1 as i16, self.data2 as i16))
        } else {
            None
        }
    }

    /// Express this MIDI event as a Frown side-channel signal.
    pub fn to_frown(&self) -> Option<Frown> {
        if self.command() == Self::NOTE_OFF {
            Some(Frown::new(self.data1 as i16, self.velocity as i16))
        } else {
            None
        }
    }
}

impl core::fmt::Display for MidiEvent {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        let cmd = match self.command() {
            0x80 => "NOTE_OFF",
            0x90 => "NOTE_ON",
            0xA0 => "POLY_AFTER",
            0xB0 => "CC",
            0xC0 => "PROG",
            0xD0 => "CH_AFTER",
            0xE0 => "PITCH",
            _ => "UNKNOWN",
        };
        write!(
            f,
            "Midi({} ch={} d1={} d2={} vel={} t={})",
            cmd,
            self.channel(),
            self.data1,
            self.data2,
            self.velocity,
            self.timestamp
        )
    }
}

// ---------------------------------------------------------------------------
// Nod/Smile/Frown from MidiEvent conversions
// ---------------------------------------------------------------------------

impl From<&MidiEvent> for Option<Nod> {
    fn from(event: &MidiEvent) -> Self {
        event.to_nod()
    }
}

impl From<&MidiEvent> for Option<Smile> {
    fn from(event: &MidiEvent) -> Self {
        event.to_smile()
    }
}

impl From<&MidiEvent> for Option<Frown> {
    fn from(event: &MidiEvent) -> Self {
        event.to_frown()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_note_on_event() {
        let e = MidiEvent::note_on(60, 100);
        assert!(e.is_note_on());
        assert!(!e.is_note_off());
        assert_eq!(e.velocity, 100);
        assert_eq!(e.data1, 60);
    }

    #[test]
    fn test_note_off_event() {
        let e = MidiEvent::note_off(60, 0);
        assert!(e.is_note_off());
        assert!(!e.is_note_on());
        assert_eq!(e.velocity, 0);
    }

    #[test]
    fn test_velocity_zero_note_on_is_off() {
        let e = MidiEvent::note_on(60, 0);
        assert!(e.is_note_off());
        assert!(!e.is_note_on());
    }

    #[test]
    fn test_control_change_event() {
        let e = MidiEvent::control_change(7, 100);
        assert_eq!(e.command(), 0xB0);
        assert_eq!(e.velocity, 100);
    }

    #[test]
    fn test_channel_extraction() {
        let e = MidiEvent::new(0x92, 60, 100, 0);
        assert_eq!(e.channel(), 2);
    }

    #[test]
    fn test_to_nod() {
        let e = MidiEvent::note_on(64, 80);
        let nod = e.to_nod();
        assert!(nod.is_some());
        assert_eq!(nod.unwrap().note, 64);
    }

    #[test]
    fn test_to_frown() {
        let e = MidiEvent::note_off(64, 0);
        let frown = e.to_frown();
        assert!(frown.is_some());
        assert_eq!(frown.unwrap().note, 64);
    }

    #[test]
    fn test_to_smile() {
        let e = MidiEvent::control_change(7, 127);
        let smile = e.to_smile();
        assert!(smile.is_some());
    }

    #[test]
    fn test_display() {
        let e = MidiEvent::note_on(60, 100);
        let s = format!("{e}");
        assert!(s.contains("NOTE_ON"));
        assert!(s.contains("vel=100"));
    }
}

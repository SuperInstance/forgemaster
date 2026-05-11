/// MIDI clock and tempo tracking utilities.

use crate::core::TZeroClock;

/// MIDI clock resolution in pulses per quarter note (PPQN).
pub const DEFAULT_PPQN: u32 = 480;

/// A MIDI clock that tracks tempo, position, and timing via T-0 clocks.
#[derive(Debug, Clone)]
pub struct MidiClock {
    /// T-0 clock for tick-level timing.
    pub clock: TZeroClock,
    /// Pulses per quarter note.
    pub ppqn: u32,
    /// Current tempo in BPM.
    pub tempo: f64,
    /// Current tick position in the sequence.
    pub position: u64,
    /// Whether the clock is running.
    pub running: bool,
}

impl MidiClock {
    /// Create a new MidiClock with default PPQN and tempo.
    #[inline]
    pub fn new() -> Self {
        MidiClock {
            clock: TZeroClock::default(),
            ppqn: DEFAULT_PPQN,
            tempo: 120.0,
            position: 0,
            running: false,
        }
    }

    /// Create a MidiClock with a custom T-0 clock.
    #[inline]
    pub fn with_clock(clock: TZeroClock) -> Self {
        MidiClock {
            clock,
            ppqn: DEFAULT_PPQN,
            tempo: 120.0,
            position: 0,
            running: false,
        }
    }

    /// Set the tempo in BPM.
    #[inline]
    pub fn set_tempo(&mut self, bpm: f64) {
        self.tempo = bpm.clamp(1.0, 999.0);
    }

    /// Advance the clock by one tick with the given wall-clock time.
    #[inline]
    pub fn tick(&mut self, now: f64) {
        if !self.running {
            self.running = true;
        }
        self.position += 1;
        self.clock.tick(now);
    }

    /// Calculate microseconds per quarter note from current tempo.
    #[inline]
    pub fn us_per_quarter_note(&self) -> f64 {
        60_000_000.0 / self.tempo
    }

    /// Convert a tick position to a beat (quarter note) position.
    #[inline]
    pub fn tick_to_beat(&self, tick: u64) -> f64 {
        tick as f64 / self.ppqn as f64
    }

    /// Convert a beat position to a tick position.
    #[inline]
    pub fn beat_to_tick(&self, beat: f64) -> u64 {
        (beat * self.ppqn as f64).round() as u64
    }

    /// Current beat position (1-based).
    #[inline]
    pub fn current_beat(&self) -> f64 {
        self.tick_to_beat(self.position)
    }

    /// Current measure (assuming 4/4 time).
    #[inline]
    pub fn current_measure(&self) -> f64 {
        self.current_beat() / 4.0
    }

    /// Reset the clock.
    #[inline]
    pub fn reset(&mut self) {
        self.clock.reset();
        self.position = 0;
        self.running = false;
    }
}

impl Default for MidiClock {
    fn default() -> Self {
        MidiClock::new()
    }
}

impl core::fmt::Display for MidiClock {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        write!(
            f,
            "MidiClock(tempo={:.1}bpm pos={} ppqn={} running={})",
            self.tempo, self.position, self.ppqn, self.running
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_midi_clock_default() {
        let mc = MidiClock::new();
        assert_eq!(mc.ppqn, DEFAULT_PPQN);
        assert!((mc.tempo - 120.0).abs() < 1e-10);
        assert!(!mc.running);
    }

    #[test]
    fn test_midi_clock_tick() {
        let mut mc = MidiClock::new();
        mc.tick(1.0);
        assert!(mc.running);
        assert_eq!(mc.position, 1);
    }

    #[test]
    fn test_midi_clock_tick_to_beat() {
        let mc = MidiClock::new();
        assert!((mc.tick_to_beat(480) - 1.0).abs() < 1e-10);
        assert!((mc.tick_to_beat(960) - 2.0).abs() < 1e-10);
    }

    #[test]
    fn test_midi_clock_beat_to_tick() {
        let mc = MidiClock::new();
        assert_eq!(mc.beat_to_tick(1.0), 480);
        assert_eq!(mc.beat_to_tick(2.5), 1200);
    }

    #[test]
    fn test_midi_clock_measure() {
        let mut mc = MidiClock::new();
        // 4 beats per measure, so 1920 ticks = 4 beats = 1 measure
        for _ in 0..1920 {
            mc.tick(1.0);
        }
        assert!((mc.current_measure() - 1.0).abs() < 0.001);
    }

    #[test]
    fn test_midi_clock_tempo_set() {
        let mut mc = MidiClock::new();
        mc.set_tempo(140.0);
        assert!((mc.tempo - 140.0).abs() < 1e-10);
    }

    #[test]
    fn test_midi_clock_us_per_qn() {
        let mc = MidiClock::new();
        let us = mc.us_per_quarter_note();
        // 60,000,000 / 120 = 500,000
        assert!((us - 500_000.0).abs() < 1e-6);
    }

    #[test]
    fn test_midi_clock_reset() {
        let mut mc = MidiClock::new();
        mc.tick(1.0);
        mc.tick(2.0);
        mc.reset();
        assert_eq!(mc.position, 0);
        assert!(!mc.running);
    }
}

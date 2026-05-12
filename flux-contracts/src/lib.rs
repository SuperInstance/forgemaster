//! FLUX OS Contracts — Frozen trait definitions
//!
//! These are the shared contracts between ALL FLUX OS components:
//! - plato-mud engine
//! - zeitgeist-protocol
//! - flux-transport
//! - All language SDKs
//!
//! CHANGE THESE AND EVERYTHING BREAKS. Freeze before integrating.
//!
//! Version: 1.0.0 (frozen 2026-05-11)

use serde::{Deserialize, Serialize};
use std::fmt;

// ── Core IDs ────────────────────────────────────────────────────────────────

/// Unique room identifier
#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
pub struct RoomId(pub String);

/// Unique tile identifier
#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
pub struct TileId(pub String);

/// Unique agent identifier
#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
pub struct AgentId(pub String);

/// Unique NPC identifier
#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
pub struct NpcId(pub String);

// ── Zeitgeist ───────────────────────────────────────────────────────────────

/// The 5-dimensional zeitgeist carried by FLUX transference
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Zeitgeist {
    pub precision: PrecisionState,
    pub confidence: ConfidenceState,
    pub trajectory: TrajectoryState,
    pub consensus: ConsensusState,
    pub temporal: TemporalState,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PrecisionState {
    /// Current deadband width (0.0 = snapped, wider = more uncertain)
    pub deadband: f64,
    /// Position in funnel (0.0 = wide/open, 1.0 = at snap point)
    pub funnel_position: f64,
    /// Whether snap is imminent
    pub snap_imminent: bool,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ConfidenceState {
    /// Bloom filter hash (32 bytes)
    pub bloom_hash: [u8; 32],
    /// XOR parity (mod-2 Euler characteristic)
    pub parity: u8,
    /// Overall certainty (0.0-1.0)
    pub certainty: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct TrajectoryState {
    /// Hurst exponent estimate (0.0-1.0, <0.5 = mean-reverting, ~0.5 = random, >0.5 = trending)
    pub hurst: f64,
    /// Current trend direction
    pub trend: Trend,
    /// Rate of change (velocity)
    pub velocity: f64,
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub enum Trend {
    Stable,
    Rising,
    Falling,
    Chaotic,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ConsensusState {
    /// Holonomy around cycles (0.0 = fully coherent, higher = drift)
    pub holonomy: f64,
    /// Fraction of peers that agree (0.0-1.0)
    pub peer_agreement: f64,
    /// CRDT version vector clock
    pub crdt_version: u64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct TemporalState {
    /// Position in beat grid (0.0-1.0)
    pub beat_position: f64,
    /// Current phase
    pub phase: Phase,
    /// How well rhythm matches grid (0.0-1.0)
    pub rhythm_coherence: f64,
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub enum Phase {
    Idle,
    Approaching,
    Snap,
    Hold,
}

impl Default for Zeitgeist {
    fn default() -> Self {
        Self {
            precision: PrecisionState {
                deadband: 1.0,
                funnel_position: 0.0,
                snap_imminent: false,
            },
            confidence: ConfidenceState {
                bloom_hash: [0u8; 32],
                parity: 0,
                certainty: 0.5,
            },
            trajectory: TrajectoryState {
                hurst: 0.5,
                trend: Trend::Stable,
                velocity: 0.0,
            },
            consensus: ConsensusState {
                holonomy: 0.0,
                peer_agreement: 1.0,
                crdt_version: 0,
            },
            temporal: TemporalState {
                beat_position: 0.0,
                phase: Phase::Idle,
                rhythm_coherence: 1.0,
            },
        }
    }
}

// ── FLUX Packet ─────────────────────────────────────────────────────────────

/// The wire format for FLUX transference between rooms
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct FluxPacket {
    /// Protocol version
    pub version: u16,
    /// Source room
    pub source: RoomId,
    /// Target room
    pub target: RoomId,
    /// Timestamp (UNIX epoch, seconds)
    pub timestamp: f64,
    /// Application payload (arbitrary bytes)
    pub payload: Vec<u8>,
    /// The zeitgeist carried by this transference
    pub zeitgeist: Zeitgeist,
    /// XOR parity check byte
    pub parity: u8,
}

impl FluxPacket {
    pub fn new(source: RoomId, target: RoomId) -> Self {
        Self {
            version: 1,
            source,
            target,
            timestamp: 0.0,
            payload: Vec::new(),
            zeitgeist: Zeitgeist::default(),
            parity: 0,
        }
    }

    /// Compute parity over all bytes
    pub fn compute_parity(&self) -> u8 {
        let json = serde_json::to_vec(self).unwrap_or_default();
        json.iter().fold(0u8, |acc, &b| acc ^ b)
    }
}

// ── Alignment ───────────────────────────────────────────────────────────────

/// The result of alignment checking
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum AlignmentVerdict {
    /// Action is within safe bounds
    Pass,
    /// Action is questionable — flag for review
    Flag { reason: String, deviation: f64 },
    /// Action violates constraints — block it
    Block { reason: String, deviation: f64 },
}

/// The 5-dimensional alignment vector
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct AlignmentVector {
    pub precision: f64,
    pub confidence: f64,
    pub trajectory: f64,
    pub consensus: f64,
    pub temporal: f64,
}

impl AlignmentVector {
    /// Compute L2 deviation from perfect alignment (all zeros)
    pub fn deviation(&self) -> f64 {
        let sum = self.precision.powi(2)
            + self.confidence.powi(2)
            + self.trajectory.powi(2)
            + self.consensus.powi(2)
            + self.temporal.powi(2);
        (sum / 5.0).sqrt()
    }
}

/// Per-room alignment thresholds (the deadband for alignment)
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct AlignmentThresholds {
    /// Green zone: deviation below this = pass
    pub green: f64,
    /// Yellow zone: deviation below this = flag
    pub yellow: f64,
    /// Red zone: deviation >= this = block
    pub red: f64,
}

impl Default for AlignmentThresholds {
    fn default() -> Self {
        Self {
            green: 0.25,
            yellow: 0.70,
            red: 0.70,
        }
    }
}

// ── Transport Trait ─────────────────────────────────────────────────────────

/// The transport abstraction — any bus, any protocol
pub trait Transport: Send + Sync {
    /// Send a FLUX packet
    fn send(&mut self, packet: &FluxPacket) -> Result<(), TransportError>;
    /// Receive a FLUX packet
    fn recv(&mut self) -> Result<FluxPacket, TransportError>;
    /// Check if connected
    fn is_connected(&self) -> bool;
    /// Get transport metadata
    fn metadata(&self) -> TransportMeta;
}

/// Transport error type
#[derive(Debug, Clone, PartialEq)]
pub enum TransportError {
    NotConnected,
    Timeout,
    PacketTooLarge { max: usize, got: usize },
    ParseError(String),
    IoError(String),
}

/// Transport metadata
#[derive(Debug, Clone, PartialEq)]
pub struct TransportMeta {
    pub name: &'static str,
    pub latency_us: Option<u64>,
    pub bandwidth_bps: Option<u64>,
    pub reliable: bool,
    pub bidirectional: bool,
}

// ── Room Loader Trait ───────────────────────────────────────────────────────

/// How the MUD engine loads room definitions
pub trait RoomLoader {
    fn load_room(&self, id: &RoomId) -> Result<RoomDef, RoomError>;
    fn load_map(&self) -> Result<MapDef, RoomError>;
    fn list_rooms(&self) -> Vec<RoomId>;
}

/// Room definition (loaded from JSON)
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RoomDef {
    pub id: RoomId,
    pub name: String,
    pub domain: String,
    pub depth: String,
    pub description: String,
    pub exits: Vec<ExitDef>,
    pub tiles: Vec<TileId>,
    pub npcs: Vec<NpcId>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ExitDef {
    pub direction: String,
    pub target: RoomId,
    pub description: String,
    pub locked: bool,
}

/// Map definition
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MapDef {
    pub rooms: Vec<RoomDef>,
}

#[derive(Debug, Clone, PartialEq)]
pub enum RoomError {
    NotFound(RoomId),
    ParseError(String),
    IoError(String),
}

// ── Display impls ───────────────────────────────────────────────────────────

impl fmt::Display for RoomId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result { write!(f, "{}", self.0) }
}
impl fmt::Display for TileId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result { write!(f, "{}", self.0) }
}
impl fmt::Display for AgentId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result { write!(f, "{}", self.0) }
}
impl fmt::Display for AlignmentVerdict {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Pass => write!(f, "PASS"),
            Self::Flag { reason, deviation } => write!(f, "FLAG({:.3}: {})", deviation, reason),
            Self::Block { reason, deviation } => write!(f, "BLOCK({:.3}: {})", deviation, reason),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn zeitgeist_default() {
        let z = Zeitgeist::default();
        assert_eq!(z.precision.deadband, 1.0);
        assert_eq!(z.confidence.parity, 0);
        assert_eq!(z.trajectory.hurst, 0.5);
        assert_eq!(z.consensus.holonomy, 0.0);
        assert_eq!(z.temporal.beat_position, 0.0);
    }

    #[test]
    fn flux_packet_roundtrip() {
        let packet = FluxPacket::new(
            RoomId("fortran-chamber".into()),
            RoomId("rust-forge".into()),
        );
        let json = serde_json::to_string(&packet).unwrap();
        let decoded: FluxPacket = serde_json::from_str(&json).unwrap();
        assert_eq!(packet, decoded);
    }

    #[test]
    fn alignment_vector_deviation() {
        let v = AlignmentVector::default();
        assert_eq!(v.deviation(), 0.0);

        let mut v2 = AlignmentVector::default();
        v2.precision = 0.5;
        v2.confidence = 0.3;
        assert!(v2.deviation() > 0.0);
        assert!(v2.deviation() < 1.0);
    }

    #[test]
    fn alignment_verdict_display() {
        let v = AlignmentVerdict::Pass;
        assert_eq!(format!("{}", v), "PASS");

        let v = AlignmentVerdict::Block { reason: "test".into(), deviation: 0.8 };
        assert!(format!("{}", v).contains("BLOCK"));
    }

    #[test]
    fn room_id_ordering() {
        let a = RoomId("a".into());
        let b = RoomId("b".into());
        assert!(a < b);
    }
}

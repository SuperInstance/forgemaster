//! PLATO MUD Engine — Core Types
//!
//! Rooms are computational domains. Tiles are structured knowledge objects.
//! NPCs are expert agents. FLUX carries zeitgeist between rooms.

extern crate alloc;

use alloc::collections::BTreeMap;
use alloc::string::String;
use alloc::vec::Vec;
use core::fmt;
use serde::{Deserialize, Serialize};

// ─── IDs ───────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct RoomId(pub String);

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct TileId(pub String);

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct NpcId(pub String);

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct AgentId(pub String);

// ─── Domain & Depth ────────────────────────────────────────────────────────

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Domain {
    Fortran,
    Rust,
    C,
    Python,
    TypeScript,
    Zig,
    Cuda,
    Concept,
    Infrastructure,
    Alignment,
}

impl Domain {
    pub fn all() -> Vec<Domain> {
        vec![
            Domain::Fortran,
            Domain::Rust,
            Domain::C,
            Domain::Python,
            Domain::TypeScript,
            Domain::Zig,
            Domain::Cuda,
            Domain::Concept,
            Domain::Infrastructure,
            Domain::Alignment,
        ]
    }

    pub fn name(&self) -> &str {
        match self {
            Domain::Fortran => "fortran",
            Domain::Rust => "rust",
            Domain::C => "c",
            Domain::Python => "python",
            Domain::TypeScript => "typescript",
            Domain::Zig => "zig",
            Domain::Cuda => "cuda",
            Domain::Concept => "concept",
            Domain::Infrastructure => "infrastructure",
            Domain::Alignment => "alignment",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Depth {
    Introductory,
    Advanced,
    Expert,
}

impl Depth {
    pub fn level(&self) -> u8 {
        match self {
            Depth::Introductory => 0,
            Depth::Advanced => 1,
            Depth::Expert => 2,
        }
    }
}

// ─── Room ───────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum RoomState {
    /// Room is dormant, no active agents
    Dormant,
    /// Agents are present and working
    Active,
    /// Knowledge is being validated/certified
    Validating,
    /// Room is merging zeitgeist from another room
    Merging,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Exit {
    pub direction: String,
    pub target: RoomId,
    pub description: String,
    pub locked: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Workbench {
    pub name: String,
    pub description: String,
    pub recipes: Vec<Recipe>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Recipe {
    pub name: String,
    pub inputs: Vec<TileId>,
    pub output: TileContent,
    pub description: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Room {
    pub id: RoomId,
    pub name: String,
    pub description: String,
    pub domain: Domain,
    pub exits: Vec<Exit>,
    pub tiles: Vec<TileId>,
    pub npcs: Vec<NpcId>,
    pub workbench: Option<Workbench>,
    pub depth: Depth,
    pub state: RoomState,
}

// ─── Tile ───────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SpatialIndex {
    /// Domain axis
    pub x: f64,
    /// Depth axis
    pub y: f64,
    /// Time axis
    pub z: f64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum TileContent {
    Theorem(String),
    Proof(String),
    Code(String),
    Benchmark(String),
    Caveat(String),
    EmpiricalData(String),
    Falsification(String),
    Constraint(String),
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum Lifecycle {
    Created,
    Validated,
    Certified,
    Superseded,
    Deprecated,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Tile {
    pub id: TileId,
    pub title: String,
    pub location: SpatialIndex,
    pub author: AgentId,
    pub confidence: f64,
    pub domain_tags: Vec<String>,
    pub links: Vec<TileId>,
    pub content: TileContent,
    pub lifecycle: Lifecycle,
    pub bloom_hash: [u8; 32],
}

// ─── NPC ────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct Query(pub String);

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct Response(pub String);

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Dialog {
    pub npc: NpcId,
    pub agent: AgentId,
    pub turns: Vec<(String, String)>,
    pub topic: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Npc {
    pub id: NpcId,
    pub name: String,
    pub room: RoomId,
    pub expertise: Vec<String>,
    pub personality: String,
    pub knowledge_graph: BTreeMap<Query, Response>,
    pub current_dialog: Option<Dialog>,
}

// ─── FLUX / Zeitgeist ──────────────────────────────────────────────────────

/// Deadband funnel state — tracks precision convergence
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FunnelState {
    pub center: f64,
    pub width: f64,
    pub samples: u64,
    pub converged: bool,
}

/// Bloom filter for certainty tracking
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BloomFilter {
    pub bits: Vec<u64>,
    pub num_hashes: u32,
    pub estimated_count: u64,
}

impl BloomFilter {
    pub fn new(num_hashes: u32, size_bits: usize) -> Self {
        let num_words = (size_bits + 63) / 64;
        Self {
            bits: alloc::vec![0u64; num_words],
            num_hashes,
            estimated_count: 0,
        }
    }

    pub fn insert(&mut self, item: &[u8]) {
        for i in 0..self.num_hashes {
            let hash = simple_hash(item, i);
            let bit = hash as usize % (self.bits.len() * 64);
            self.bits[bit / 64] |= 1u64 << (bit % 64);
        }
        self.estimated_count += 1;
    }

    pub fn contains(&self, item: &[u8]) -> bool {
        for i in 0..self.num_hashes {
            let hash = simple_hash(item, i);
            let bit = hash as usize % (self.bits.len() * 64);
            if self.bits[bit / 64] & (1u64 << (bit % 64)) == 0 {
                return false;
            }
        }
        true
    }

    /// Merge two bloom filters (bitwise OR) — CRDT merge
    pub fn merge(&mut self, other: &BloomFilter) {
        for (i, word) in other.bits.iter().enumerate() {
            if i < self.bits.len() {
                self.bits[i] |= word;
            }
        }
        self.estimated_count = core::cmp::max(self.estimated_count, other.estimated_count);
    }
}

fn simple_hash(data: &[u8], seed: u32) -> u64 {
    let mut hash: u64 = 0xcbf29ce484222325;
    hash = hash.wrapping_add(seed as u64);
    for &byte in data {
        hash ^= byte as u64;
        hash = hash.wrapping_mul(0x100000001b3);
    }
    hash
}

/// Hurst exponent estimate for trend detection
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HurstEstimate {
    pub value: f64,
    pub confidence: f64,
    pub sample_count: u64,
}

/// Holonomy state — cycle coherence tracking
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HolonomyState {
    pub cycle_count: u64,
    pub coherence: f64,
    pub last_check: f64,
}

/// Beat position — temporal rhythm
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BeatPosition {
    pub beat: u64,
    pub tempo: f64,
    pub phase: f64,
}

/// The zeitgeist carried by FLUX transference
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Zeitgeist {
    pub precision: FunnelState,
    pub confidence: BloomFilter,
    pub trajectory: HurstEstimate,
    pub consensus: HolonomyState,
    pub temporal: BeatPosition,
}

impl Zeitgeist {
    pub fn new() -> Self {
        Self {
            precision: FunnelState {
                center: 0.0,
                width: 1.0,
                samples: 0,
                converged: false,
            },
            confidence: BloomFilter::new(3, 256),
            trajectory: HurstEstimate {
                value: 0.5,
                confidence: 0.0,
                sample_count: 0,
            },
            consensus: HolonomyState {
                cycle_count: 0,
                coherence: 0.0,
                last_check: 0.0,
            },
            temporal: BeatPosition {
                beat: 0,
                tempo: 120.0,
                phase: 0.0,
            },
        }
    }

    /// CRDT merge — commutative, associative, idempotent
    pub fn merge(&mut self, other: &Zeitgeist) {
        // Precision: narrowest funnel wins (most precise)
        if other.precision.width < self.precision.width {
            self.precision = other.precision.clone();
        }
        self.precision.samples += other.precision.samples;

        // Confidence: bloom filter OR (CRDT)
        self.confidence.merge(&other.confidence);

        // Trajectory: highest confidence estimate
        if other.trajectory.confidence > self.trajectory.confidence {
            self.trajectory = other.trajectory.clone();
        }

        // Consensus: max coherence
        self.consensus.cycle_count = core::cmp::max(self.consensus.cycle_count, other.consensus.cycle_count);
        self.consensus.coherence = self.consensus.coherence.max(other.consensus.coherence);

        // Temporal: latest beat
        self.temporal.beat = core::cmp::max(self.temporal.beat, other.temporal.beat);
    }
}

// ─── FLUX Transference ──────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum TransferencePayload {
    Tile(Tile),
    Knowledge(String),
    StateUpdate(RoomState),
    AlignmentCheck(AlignmentReport),
    Heartbeat,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AlignmentReport {
    pub constraint_id: u8,
    pub passed: bool,
    pub message: String,
    pub severity: AlignmentSeverity,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum AlignmentSeverity {
    Info,
    Warning,
    Block,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FluxTransference {
    pub source: RoomId,
    pub target: RoomId,
    pub timestamp: f64,
    pub payload: TransferencePayload,
    pub zeitgeist: Zeitgeist,
}

// ─── Commands ───────────────────────────────────────────────────────────────

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Command {
    Look,
    Go(String),
    Get(String),
    Drop(String),
    Talk(String),
    Craft(Vec<String>),
    Inventory,
    Map,
    Help,
    Examine(String),
    Status,
}

impl fmt::Display for Command {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Command::Look => write!(f, "LOOK"),
            Command::Go(dir) => write!(f, "GO {}", dir),
            Command::Get(item) => write!(f, "GET {}", item),
            Command::Drop(item) => write!(f, "DROP {}", item),
            Command::Talk(npc) => write!(f, "TALK {}", npc),
            Command::Craft(items) => write!(f, "CRAFT {}", items.join(" + ")),
            Command::Inventory => write!(f, "INVENTORY"),
            Command::Map => write!(f, "MAP"),
            Command::Help => write!(f, "HELP"),
            Command::Examine(t) => write!(f, "EXAMINE {}", t),
            Command::Status => write!(f, "STATUS"),
        }
    }
}

// ─── Agent Session ──────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentSession {
    pub agent_id: AgentId,
    pub current_room: RoomId,
    pub inventory: Vec<TileId>,
    pub connected_at: f64,
}

// ─── Transport ──────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TransportConfig {
    pub transport_type: String,
    pub address: String,
    pub port: u16,
    pub options: BTreeMap<String, String>,
}

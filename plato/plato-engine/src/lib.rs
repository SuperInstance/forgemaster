pub mod tile;
pub mod room;
pub mod gate;
pub mod engine;
pub mod pathfinder;
pub mod server;

// Re-exports
pub use tile::{Tile, TileBuilder, TileHash, Provenance, TileValidationError};
pub use room::{Room, RoomStats};
pub use gate::{Gate, GateConfig, GateDecision};
pub use engine::{PlatoEngine, HealthStatus, EngineStats, GateRejection};
pub use pathfinder::{Pathfinder, RoomHop};

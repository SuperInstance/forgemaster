use dashmap::DashMap;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use std::time::Instant;

use crate::gate::{Gate, GateConfig, GateDecision};
use crate::room::Room;
use crate::tile::{Tile, TileHash};

/// Statistics tracked by the engine.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct EngineStats {
    pub total_submitted: u64,
    pub total_accepted: u64,
    pub total_rejected: u64,
    pub rejection_reasons: HashMap<String, u64>,
}

/// Engine health status.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthStatus {
    pub rooms_count: usize,
    pub tiles_count: usize,
    pub uptime_seconds: f64,
    pub stats: EngineStats,
}

/// Reason a tile was rejected by the gate.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GateRejection {
    pub reason: String,
    pub tile_id: Option<uuid::Uuid>,
}

/// The core PLATO engine — thread-safe, concurrent tile management.
pub struct PlatoEngine {
    rooms: DashMap<String, Room>,
    gate: Gate,
    stats: Arc<EngineStatsInner>,
    started_at: Instant,
}

/// Internal stats with atomics for lock-free updates.
struct EngineStatsInner {
    total_submitted: AtomicU64,
    total_accepted: AtomicU64,
    total_rejected: AtomicU64,
    rejection_reasons: dashmap::DashMap<String, AtomicU64>,
}

impl PlatoEngine {
    pub fn new(gate_config: GateConfig) -> Self {
        Self {
            rooms: DashMap::new(),
            gate: Gate::new(gate_config),
            stats: Arc::new(EngineStatsInner {
                total_submitted: AtomicU64::new(0),
                total_accepted: AtomicU64::new(0),
                total_rejected: AtomicU64::new(0),
                rejection_reasons: DashMap::new(),
            }),
            started_at: Instant::now(),
        }
    }

    pub fn with_defaults() -> Self {
        Self::new(GateConfig::default())
    }

    /// Submit a tile through the quality gate into a room.
    /// Returns the tile's content hash on success, or a rejection reason.
    pub fn submit(&self, room_id: &str, tile: Tile) -> Result<TileHash, GateRejection> {
        self.stats.total_submitted.fetch_add(1, Ordering::Relaxed);

        // Get existing hashes for duplicate check
        let existing_hashes: Vec<String> = if let Some(room) = self.rooms.get(room_id) {
            room.hash_index.iter().map(|(h, _)| h.clone()).collect()
        } else {
            Vec::new()
        };

        // Evaluate through gate
        let decision = self.gate.evaluate_with_hashes(&tile, &existing_hashes);

        match decision {
            GateDecision::Accept => {
                let hash = tile.content_hash();

                // Insert into room
                self.rooms
                    .entry(room_id.to_string())
                    .or_insert_with(|| Room::new(room_id, &tile.domain))
                    .insert_tile(tile);

                self.stats.total_accepted.fetch_add(1, Ordering::Relaxed);
                Ok(hash)
            }
            GateDecision::Reject(reason) => {
                // Track rejection reason
                self.stats
                    .rejection_reasons
                    .entry(reason.clone())
                    .or_insert_with(|| AtomicU64::new(0))
                    .fetch_add(1, Ordering::Relaxed);

                self.stats.total_rejected.fetch_add(1, Ordering::Relaxed);

                Err(GateRejection {
                    reason,
                    tile_id: Some(tile.id),
                })
            }
        }
    }

    /// Query tiles from a room with optional tag filter and limit.
    pub fn query(&self, room_id: &str, tag: Option<&str>, limit: usize) -> Vec<Tile> {
        if let Some(room) = self.rooms.get(room_id) {
            let tiles: Vec<Tile> = match tag {
                Some(t) => room.query_by_tag(t).into_iter().cloned().collect(),
                None => room.tiles.clone(),
            };
            tiles.into_iter().take(limit).collect()
        } else {
            Vec::new()
        }
    }

    /// List room IDs, optionally filtered by prefix.
    pub fn list_rooms(&self, prefix: Option<&str>) -> Vec<String> {
        self.rooms
            .iter()
            .filter_map(|r| {
                match prefix {
                    Some(p) if !r.key().starts_with(p) => None,
                    _ => Some(r.key().clone()),
                }
            })
            .collect()
    }

    /// Get a room by ID.
    pub fn get_room(&self, room_id: &str) -> Option<Room> {
        self.rooms.get(room_id).map(|r| r.value().clone())
    }

    /// Health check — rooms count, tiles count, uptime, stats.
    pub fn health(&self) -> HealthStatus {
        let rooms_count = self.rooms.len();
        let tiles_count: usize = self.rooms.iter().map(|r| r.tile_count()).sum();

        HealthStatus {
            rooms_count,
            tiles_count,
            uptime_seconds: self.started_at.elapsed().as_secs_f64(),
            stats: self.get_stats(),
        }
    }

    /// Get current engine stats.
    pub fn get_stats(&self) -> EngineStats {
        let mut rejection_reasons = HashMap::new();
        for entry in self.stats.rejection_reasons.iter() {
            rejection_reasons.insert(entry.key().clone(), entry.value().load(Ordering::Relaxed));
        }

        EngineStats {
            total_submitted: self.stats.total_submitted.load(Ordering::Relaxed),
            total_accepted: self.stats.total_accepted.load(Ordering::Relaxed),
            total_rejected: self.stats.total_rejected.load(Ordering::Relaxed),
            rejection_reasons,
        }
    }
}

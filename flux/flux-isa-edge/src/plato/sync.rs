use std::collections::HashMap;
use std::sync::Arc;
use std::time::Duration;
use serde::{Deserialize, Serialize};
use tokio::sync::RwLock;
use uuid::Uuid;
use super::client::{PlatoClient, Tile};

/// Local cache configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncConfig {
    /// Rooms to sync from PLATO.
    pub rooms: Vec<String>,
    /// How often to resync (seconds).
    pub sync_interval: Duration,
    /// Whether to start in offline mode.
    pub offline_mode: bool,
}

impl Default for SyncConfig {
    fn default() -> Self {
        SyncConfig {
            rooms: vec!["forgemaster".into(), "fleet-ops".into()],
            sync_interval: Duration::from_secs(300),
            offline_mode: false,
        }
    }
}

/// In-memory PLATO cache (SQLite-grade for edge workloads under 6 GB RAM).
pub struct PlatoCache {
    /// room → (tile_id → tile)
    tiles: Arc<RwLock<HashMap<String, HashMap<Uuid, Tile>>>>,
    /// Tiles created locally while offline.
    pending: Arc<RwLock<Vec<Tile>>>,
}

impl PlatoCache {
    pub fn new() -> Self {
        PlatoCache {
            tiles: Arc::new(RwLock::new(HashMap::new())),
            pending: Arc::new(RwLock::new(Vec::new())),
        }
    }

    /// Sync a room's tiles into cache. Server wins for existing tiles.
    pub async fn sync_room(&self, room: &str, server_tiles: Vec<Tile>) {
        let mut tiles = self.tiles.write().await;
        let room_map = tiles.entry(room.to_string()).or_insert_with(HashMap::new);
        for tile in server_tiles {
            room_map.insert(tile.id, tile);
        }
        tracing::info!(room, count = room_map.len(), "synced room");
    }

    /// Add a tile to local cache (for offline creation).
    pub async fn add_local(&self, tile: Tile) {
        let room = tile.room.clone();
        {
            let mut tiles = self.tiles.write().await;
            let room_map = tiles.entry(room.clone()).or_insert_with(HashMap::new);
            room_map.insert(tile.id, tile.clone());
        }
        let mut pending = self.pending.write().await;
        pending.push(tile);
        tracing::debug!(room, "added local tile (pending sync)");
    }

    /// Query cached tiles in a room.
    pub async fn query_room(&self, room: &str) -> Vec<Tile> {
        let tiles = self.tiles.read().await;
        tiles.get(room).map(|m| m.values().cloned().collect()).unwrap_or_default()
    }

    /// Get pending tiles (those created offline).
    pub async fn drain_pending(&self) -> Vec<Tile> {
        let mut pending = self.pending.write().await;
        std::mem::take(&mut *pending)
    }

    /// Number of cached tiles across all rooms.
    pub async fn total_cached(&self) -> usize {
        let tiles = self.tiles.read().await;
        tiles.values().map(|m| m.len()).sum()
    }
}

/// Background sync task handle.
pub struct SyncHandle {
    shutdown: tokio::sync::watch::Sender<bool>,
}

impl SyncHandle {
    /// Signal the background sync to stop.
    pub fn stop(&self) {
        let _ = self.shutdown.send(true);
    }
}

/// Start the background sync loop.
pub fn start_background_sync(
    client: PlatoClient,
    cache: Arc<PlatoCache>,
    config: SyncConfig,
) -> SyncHandle {
    let (tx, mut rx) = tokio::sync::watch::channel(false);

    tokio::spawn(async move {
        let mut interval = tokio::time::interval(config.sync_interval);
        loop {
            tokio::select! {
                _ = interval.tick() => {
                    for room in &config.rooms {
                        match client.query(room, "*").await {
                            Ok(tiles) => cache.sync_room(room, tiles).await,
                            Err(e) => {
                                tracing::warn!(room, error = %e, "sync failed, operating from cache");
                            }
                        }
                    }
                    // Flush pending tiles.
                    let pending = cache.drain_pending().await;
                    for tile in pending {
                        match client.submit(tile.clone()).await {
                            Ok(_) => tracing::info!("flushed pending tile"),
                            Err(e) => {
                                tracing::warn!(error = %e, "failed to flush pending tile, re-queueing");
                                cache.add_local(tile).await;
                            }
                        }
                    }
                }
                _ = rx.changed() => {
                    tracing::info!("background sync shutting down");
                    break;
                }
            }
        }
    });

    SyncHandle { shutdown: tx }
}

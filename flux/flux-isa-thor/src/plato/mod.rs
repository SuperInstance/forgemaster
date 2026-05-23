pub mod cache;
pub mod client;
pub mod pathfinder;

use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::RwLock;

/// A PLATO knowledge tile.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Tile {
    pub id: uuid::Uuid,
    pub room_id: String,
    pub content: serde_json::Value,
    pub confidence: f64,
    pub tags: Vec<String>,
    pub created_at: u64,
}

/// PLATO room summary.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Room {
    pub id: String,
    pub name: String,
    pub tile_count: u64,
    pub last_updated: u64,
}

/// Handle shared across the VM and pipeline.
#[derive(Debug)]
pub struct PlatoHandle {
    client: Arc<client::PlatoClient>,
    cache: Arc<RwLock<cache::TileCache>>,
}

impl PlatoHandle {
    pub fn new(client: Arc<client::PlatoClient>, cache: Arc<RwLock<cache::TileCache>>) -> Self {
        Self { client, cache }
    }

    pub fn client(&self) -> &Arc<client::PlatoClient> {
        &self.client
    }

    pub async fn cache(&self) -> tokio::sync::RwLockReadGuard<'_, cache::TileCache> {
        self.cache.read().await
    }

    pub async fn cache_mut(&self) -> tokio::sync::RwLockWriteGuard<'_, cache::TileCache> {
        self.cache.write().await
    }
}

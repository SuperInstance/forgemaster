use serde::{Deserialize, Serialize};
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::Semaphore;
use tracing::{debug, warn};
use uuid::Uuid;

use super::{Room, Tile};

/// Async PLATO HTTP client with connection pooling.
#[derive(Debug)]
pub struct PlatoClient {
    base_url: String,
    http: reqwest::Client,
    semaphore: Arc<Semaphore>,
    timeout: Duration,
}

#[derive(Debug, thiserror::Error)]
pub enum PlatoError {
    #[error("HTTP error: {0}")]
    Http(#[from] reqwest::Error),
    #[error("Not found: {0}")]
    NotFound(String),
    #[error("Rate limited")]
    RateLimited,
    #[error("Gate rejected: {0}")]
    GateRejected(String),
    #[error("Serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
}

impl PlatoClient {
    pub fn new(base_url: &str, max_concurrent: usize, timeout: Duration) -> Self {
        let http = reqwest::Client::builder()
            .pool_max_idle_per_host(max_concurrent)
            .timeout(timeout)
            .build()
            .expect("failed to build reqwest client");
        Self {
            base_url: base_url.trim_end_matches('/').to_string(),
            http,
            semaphore: Arc::new(Semaphore::new(max_concurrent)),
            timeout,
        }
    }

    /// Fetch a room by ID.
    pub async fn get_room(&self, room_id: &str) -> Result<Room, PlatoError> {
        let _permit = self.semaphore.acquire().await.unwrap();
        let url = format!("{}/rooms/{room_id}", self.base_url);
        debug!("GET {url}");
        let resp = self.http.get(&url).send().await?;
        if resp.status() == reqwest::StatusCode::NOT_FOUND {
            return Err(PlatoError::NotFound(room_id.to_string()));
        }
        let room: Room = resp.error_for_status()?.json().await?;
        Ok(room)
    }

    /// Fetch tiles from a room.
    pub async fn get_tiles(&self, room_id: &str) -> Result<Vec<Tile>, PlatoError> {
        let _permit = self.semaphore.acquire().await.unwrap();
        let url = format!("{}/rooms/{room_id}/tiles", self.base_url);
        debug!("GET {url}");
        let resp = self.http.get(&url).send().await?;
        let tiles: Vec<Tile> = resp.error_for_status()?.json().await?;
        Ok(tiles)
    }

    /// Submit a single tile.
    pub async fn submit_tile(&self, tile: &Tile) -> Result<(), PlatoError> {
        let _permit = self.semaphore.acquire().await.unwrap();
        let url = format!("{}/rooms/{}/tiles", self.base_url, tile.room_id);
        debug!("POST {url} — tile {}", tile.id);
        let resp = self.http.post(&url).json(tile).send().await?;
        if resp.status() == reqwest::StatusCode::CONFLICT {
            let body = resp.text().await.unwrap_or_default();
            return Err(PlatoError::GateRejected(body));
        }
        resp.error_for_status()?;
        Ok(())
    }

    /// Batch submit tiles — up to 1000 in one call.
    pub async fn submit_tiles_batch(&self, tiles: &[Tile]) -> Result<usize, PlatoError> {
        if tiles.is_empty() {
            return Ok(0);
        }
        let _permit = self.semaphore.acquire().await.unwrap();
        let mut by_room: std::collections::HashMap<String, Vec<&Tile>> =
            std::collections::HashMap::new();
        for t in tiles {
            by_room.entry(t.room_id.clone()).or_default().push(t);
        }

        let mut submitted = 0usize;
        for (room_id, room_tiles) in by_room {
            let url = format!("{}/rooms/{room_id}/tiles/batch", self.base_url);
            debug!("POST {url} — {} tiles", room_tiles.len());
            let resp = self.http.post(&url).json(&room_tiles).send().await?;
            if resp.status() == reqwest::StatusCode::CONFLICT {
                let body = resp.text().await.unwrap_or_default();
                warn!("Gate rejected batch for room {room_id}: {body}");
                continue;
            }
            resp.error_for_status()?;
            submitted += room_tiles.len();
        }
        Ok(submitted)
    }

    /// Search tiles across rooms.
    pub async fn search(&self, query: &str, limit: usize) -> Result<Vec<Tile>, PlatoError> {
        let _permit = self.semaphore.acquire().await.unwrap();
        let url = format!("{}/search", self.base_url);
        debug!("GET {url} — q={query}, limit={limit}");
        let resp = self
            .http
            .get(&url)
            .query(&[("q", query), ("limit", &limit.to_string())])
            .send()
            .await?;
        let tiles: Vec<Tile> = resp.error_for_status()?.json().await?;
        Ok(tiles)
    }

    /// Health check.
    pub async fn health(&self) -> Result<bool, PlatoError> {
        let url = format!("{}/health", self.base_url);
        let resp = self.http.get(&url).send().await;
        match resp {
            Ok(r) => Ok(r.status().is_success()),
            Err(e) => {
                warn!("PLATO health check failed: {e}");
                Ok(false)
            }
        }
    }
}

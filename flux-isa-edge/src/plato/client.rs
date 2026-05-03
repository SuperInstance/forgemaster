use std::time::Duration;
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// A PLATO tile (unit of knowledge).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Tile {
    pub id: Uuid,
    pub room: String,
    pub content: String,
    pub timestamp: u64,
    pub tags: Vec<String>,
}

/// PLATO client configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PlatoConfig {
    pub url: String,
    pub connect_timeout: Duration,
    pub request_timeout: Duration,
    pub max_retries: u32,
    pub base_backoff: Duration,
    pub max_backoff: Duration,
}

impl Default for PlatoConfig {
    fn default() -> Self {
        PlatoConfig {
            url: "http://localhost:8080".into(),
            connect_timeout: Duration::from_secs(5),
            request_timeout: Duration::from_secs(30),
            max_retries: 3,
            base_backoff: Duration::from_millis(500),
            max_backoff: Duration::from_secs(10),
        }
    }
}

/// Response from PLATO health endpoint.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthResponse {
    pub status: String,
    pub version: String,
    pub uptime_secs: f64,
}

/// Response from a PLATO query.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QueryResponse {
    pub tiles: Vec<Tile>,
    pub total: usize,
}

/// Async PLATO client with retry logic.
pub struct PlatoClient {
    config: PlatoConfig,
    http: reqwest::Client,
}

impl PlatoClient {
    /// Create a new PLATO client.
    pub async fn connect(config: PlatoConfig) -> Result<Self, PlatoError> {
        let http = reqwest::Client::builder()
            .connect_timeout(config.connect_timeout)
            .timeout(config.request_timeout)
            .build()
            .map_err(PlatoError::Http)?;

        let client = PlatoClient { config, http };

        // Verify connectivity.
        client.health().await?;

        Ok(client)
    }

    /// Create client without connectivity check (for offline-first).
    pub fn new_unchecked(config: PlatoConfig) -> Self {
        let http = reqwest::Client::builder()
            .connect_timeout(config.connect_timeout)
            .timeout(config.request_timeout)
            .build()
            .expect("failed to build HTTP client");
        PlatoClient { config, http }
    }

    /// Submit a tile through PLATO gate.
    pub async fn submit(&self, tile: Tile) -> Result<Tile, PlatoError> {
        self.retry(|| async {
            let resp = self.http
                .post(format!("{}/api/tiles", self.config.url))
                .json(&tile)
                .send()
                .await?;
            let status = resp.status();
            if status.is_success() {
                resp.json::<Tile>().await.map_err(PlatoError::from)
            } else {
                let body = resp.text().await.unwrap_or_default();
                Err(PlatoError::Server(format!("submit failed ({}): {}", status, body)))
            }
        }).await
    }

    /// Query tiles in a room.
    pub async fn query(&self, room: &str, query: &str) -> Result<Vec<Tile>, PlatoError> {
        self.retry(|| async {
            let resp = self.http
                .get(format!("{}/api/rooms/{}/query", self.config.url, room))
                .query(&[("q", query)])
                .send()
                .await?;
            let status = resp.status();
            if status.is_success() {
                let qr: QueryResponse = resp.json().await?;
                Ok(qr.tiles)
            } else {
                let body = resp.text().await.unwrap_or_default();
                Err(PlatoError::Server(format!("query failed ({}): {}", status, body)))
            }
        }).await
    }

    /// List all rooms.
    pub async fn list_rooms(&self) -> Result<Vec<String>, PlatoError> {
        self.retry(|| async {
            let resp = self.http
                .get(format!("{}/api/rooms", self.config.url))
                .send()
                .await?;
            let status = resp.status();
            if status.is_success() {
                resp.json::<Vec<String>>().await.map_err(PlatoError::from)
            } else {
                let body = resp.text().await.unwrap_or_default();
                Err(PlatoError::Server(format!("list_rooms failed ({}): {}", status, body)))
            }
        }).await
    }

    /// Health check.
    pub async fn health(&self) -> Result<HealthResponse, PlatoError> {
        let resp = self.http
            .get(format!("{}/health", self.config.url))
            .send()
            .await?;
        resp.json::<HealthResponse>().await.map_err(PlatoError::from)
    }

    async fn retry<F, Fut, T>(&self, f: F) -> Result<T, PlatoError>
    where
        F: Fn() -> Fut,
        Fut: std::future::Future<Output = Result<T, PlatoError>>,
    {
        let mut last_err = None;
        for attempt in 0..=self.config.max_retries {
            match f().await {
                Ok(v) => return Ok(v),
                Err(e) => {
                    last_err = Some(e);
                    if attempt < self.config.max_retries {
                        let delay = self.config.base_backoff * 2u32.saturating_pow(attempt);
                        let delay = delay.min(self.config.max_backoff);
                        tokio::time::sleep(delay).await;
                    }
                }
            }
        }
        Err(last_err.unwrap())
    }
}

/// PLATO client errors.
#[derive(Debug, thiserror::Error)]
pub enum PlatoError {
    #[error("HTTP error: {0}")]
    Http(#[from] reqwest::Error),
    #[error("Server error: {0}")]
    Server(String),
    #[error("Not connected")]
    NotConnected,
}

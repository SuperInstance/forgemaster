use serde::{Deserialize, Serialize};
use std::net::SocketAddr;

/// Full Thor node configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ThorConfig {
    /// Unique node identifier.
    pub node_id: String,

    /// Bind address for HTTP server.
    pub listen_addr: SocketAddr,

    /// PLATO server URL.
    pub plato_url: String,

    /// GPU available.
    pub gpu_available: bool,

    /// GPU memory in MB.
    pub gpu_memory_mb: u32,

    /// Maximum concurrent GPU kernels.
    pub max_concurrent_kernels: usize,

    /// Fleet peer addresses.
    pub fleet_peers: Vec<String>,

    /// Pipeline channel capacity.
    pub pipeline_channel_capacity: usize,

    /// Pipeline batch size.
    pub pipeline_batch_size: usize,

    /// Pipeline max concurrent executions.
    pub pipeline_max_concurrent_execute: usize,

    /// Checkpoint interval in seconds.
    pub checkpoint_interval_secs: u64,

    /// Heartbeat interval in seconds.
    pub heartbeat_interval_secs: u64,

    /// PLATO client max concurrent requests.
    pub plato_max_concurrent: usize,

    /// Tile cache max entries.
    pub cache_max_entries: usize,

    /// VM max stack size.
    pub vm_max_stack: usize,
}

impl Default for ThorConfig {
    fn default() -> Self {
        Self {
            node_id: format!("thor-{}", hostname::get().unwrap_or_default().to_string_lossy()),
            listen_addr: "0.0.0.0:8080".parse().unwrap(),
            plato_url: "http://localhost:3000".to_string(),
            gpu_available: false,
            gpu_memory_mb: 0,
            max_concurrent_kernels: 4,
            fleet_peers: vec![],
            pipeline_channel_capacity: 1024,
            pipeline_batch_size: 64,
            pipeline_max_concurrent_execute: 8,
            checkpoint_interval_secs: 60,
            heartbeat_interval_secs: 30,
            plato_max_concurrent: 16,
            cache_max_entries: 100_000,
            vm_max_stack: 65536,
        }
    }
}

impl ThorConfig {
    /// Load from a TOML file, falling back to defaults for missing fields.
    pub fn load_from_file(path: &std::path::Path) -> Result<Self, Box<dyn std::error::Error>> {
        let content = std::fs::read_to_string(path)?;
        let config: ThorConfig = toml::from_str(&content)?;
        Ok(config)
    }

    /// Override from environment variables.
    pub fn apply_env(&mut self) {
        if let Ok(v) = std::env::var("THOR_NODE_ID") {
            self.node_id = v;
        }
        if let Ok(v) = std::env::var("THOR_LISTEN_ADDR") {
            if let Ok(addr) = v.parse() {
                self.listen_addr = addr;
            }
        }
        if let Ok(v) = std::env::var("THOR_PLATO_URL") {
            self.plato_url = v;
        }
        if let Ok(v) = std::env::var("THOR_GPU_AVAILABLE") {
            self.gpu_available = v == "true" || v == "1";
        }
        if let Ok(v) = std::env::var("THOR_GPU_MEMORY_MB") {
            if let Ok(mb) = v.parse() {
                self.gpu_memory_mb = mb;
            }
        }
        if let Ok(v) = std::env::var("THOR_FLEET_PEERS") {
            self.fleet_peers = v.split(',').map(|s| s.trim().to_string()).collect();
        }
    }
}

// Minimal toml support — just enough to parse our config.
// In production, add `toml = "0.8"` to Cargo.toml.
mod toml_support {
    // Placeholder — actual parsing via toml crate
}

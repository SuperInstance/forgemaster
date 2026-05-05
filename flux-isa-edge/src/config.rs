use serde::{Deserialize, Serialize};

/// Edge node configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    /// Unique node identifier.
    pub node_id: String,
    /// PLATO server URL.
    pub plato_url: String,
    /// HTTP server bind address.
    pub bind_addr: String,
    /// HTTP server port.
    pub port: u16,
    /// PLATO sync interval in seconds.
    pub sync_interval_secs: u64,
    /// VM max steps.
    pub max_steps: u64,
    /// VM max time in seconds.
    pub max_time_secs: f64,
    /// VM max stack depth.
    pub max_stack_depth: usize,
    /// Sensor batch size.
    pub batch_size: usize,
    /// Violation policy: "log_and_continue" or "halt".
    pub violation_policy: String,
}

impl Default for Config {
    fn default() -> Self {
        Config {
            node_id: format!("edge-{}", hostname_or_default()),
            plato_url: "http://localhost:8080".into(),
            bind_addr: "0.0.0.0".into(),
            port: 9090,
            sync_interval_secs: 300,
            max_steps: 1_000_000,
            max_time_secs: 30.0,
            max_stack_depth: 1024,
            batch_size: 64,
            violation_policy: "log_and_continue".into(),
        }
    }
}

impl Config {
    /// Load config from environment variables (FLUX_ prefix).
    pub fn load_from_env() -> Self {
        let mut config = Config::default();
        if let Ok(v) = std::env::var("FLUX_NODE_ID") { config.node_id = v; }
        if let Ok(v) = std::env::var("FLUX_PLATO_URL") { config.plato_url = v; }
        if let Ok(v) = std::env::var("FLUX_BIND_ADDR") { config.bind_addr = v; }
        if let Ok(v) = std::env::var("FLUX_PORT") { config.port = v.parse().unwrap_or(9090); }
        if let Ok(v) = std::env::var("FLUX_SYNC_INTERVAL") { config.sync_interval_secs = v.parse().unwrap_or(300); }
        if let Ok(v) = std::env::var("FLUX_MAX_STEPS") { config.max_steps = v.parse().unwrap_or(1_000_000); }
        if let Ok(v) = std::env::var("FLUX_MAX_TIME_SECS") { config.max_time_secs = v.parse().unwrap_or(30.0); }
        if let Ok(v) = std::env::var("FLUX_MAX_STACK_DEPTH") { config.max_stack_depth = v.parse().unwrap_or(1024); }
        if let Ok(v) = std::env::var("FLUX_BATCH_SIZE") { config.batch_size = v.parse().unwrap_or(64); }
        if let Ok(v) = std::env::var("FLUX_VIOLATION_POLICY") { config.violation_policy = v; }
        config
    }

    /// Load config: tries environment variables (with defaults).
    pub fn load() -> Self {
        Config::load_from_env()
    }
}

fn hostname_or_default() -> String {
    std::env::var("HOSTNAME")
        .or_else(|_| std::env::var("HOST"))
        .unwrap_or_else(|_| "unknown".into())
}

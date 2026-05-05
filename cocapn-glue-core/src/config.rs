//! Configuration from environment variables (GLUE_* prefix).
//!
//! Requires `std` feature for env var access.

/// Core configuration for the glue protocol.
#[derive(Clone, Debug)]
pub struct Config {
    /// Our tier ID (from GLUE_TIER_ID hex string).
    pub tier_id_bytes: [u8; 8],
    /// Protocol version we advertise.
    pub protocol_version: u16,
    /// Maximum message size in bytes.
    pub max_message_size: usize,
    /// PLATO sync interval in milliseconds.
    pub plato_sync_interval_ms: u64,
    /// Beacon broadcast interval in milliseconds.
    pub beacon_interval_ms: u64,
}

impl Default for Config {
    fn default() -> Self {
        Config {
            tier_id_bytes: [0; 8],
            protocol_version: 1,
            max_message_size: 65536,
            plato_sync_interval_ms: 5000,
            beacon_interval_ms: 1000,
        }
    }
}

#[cfg(feature = "std")]
impl Config {
    /// Load configuration from environment variables.
    pub fn from_env() -> Self {
        use std::env;
        Config {
            tier_id_bytes: env::var("GLUE_TIER_ID")
                .ok()
                .and_then(|s| hex::decode(s).ok())
                .and_then(|v| {
                    if v.len() == 8 {
                        let mut arr = [0u8; 8];
                        arr.copy_from_slice(&v);
                        Some(arr)
                    } else {
                        None
                    }
                })
                .unwrap_or([0; 8]),
            protocol_version: env::var("GLUE_PROTOCOL_VERSION")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(1),
            max_message_size: env::var("GLUE_MAX_MESSAGE_SIZE")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(65536),
            plato_sync_interval_ms: env::var("GLUE_PLATO_SYNC_INTERVAL_MS")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(5000),
            beacon_interval_ms: env::var("GLUE_BEACON_INTERVAL_MS")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(1000),
        }
    }
}

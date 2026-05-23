use std::env;

#[derive(Debug, Clone)]
pub struct Config {
    pub db_path: String,
    pub batch_size: usize,
    pub listen_addr: String,
}

impl Config {
    pub fn from_env() -> Self {
        Self {
            db_path: env::var("PROVENANCE_DB_PATH")
                .unwrap_or_else(|_| "provenance_db".into()),
            batch_size: env::var("PROVENANCE_BATCH_SIZE")
                .ok()
                .and_then(|s| s.parse().ok())
                .unwrap_or(1000),
            listen_addr: env::var("PROVENANCE_LISTEN_ADDR")
                .unwrap_or_else(|_| "0.0.0.0:3010".into()),
        }
    }
}

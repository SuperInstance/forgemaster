use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TransportConfig {
    pub transports: Vec<TransportEntry>,
}

impl Default for TransportConfig {
    fn default() -> Self {
        Self { transports: vec![] }
    }
}

impl TransportConfig {
    pub fn with(mut self, entry: TransportEntry) -> Self {
        self.transports.push(entry);
        self
    }

    pub fn get(&self, name: &str) -> Option<&TransportEntry> {
        self.transports.iter().find(|t| t.name == name)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TransportEntry {
    pub name: String,
    pub kind: TransportKind,
    #[serde(default = "default_true")]
    pub enabled: bool,
    #[serde(default)]
    pub settings: HashMap<String, String>,
}

fn default_true() -> bool {
    true
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum TransportKind {
    Tcp,
    WebSocket,
    Grpc,
    Http,
    Mqtt,
    Coap,
    Serial,
    Can,
    I2c,
    Spi,
    Memory,
    File,
}

impl TransportKind {
    pub fn name(&self) -> &'static str {
        match self {
            TransportKind::Tcp => "tcp",
            TransportKind::WebSocket => "websocket",
            TransportKind::Grpc => "grpc",
            TransportKind::Http => "http",
            TransportKind::Mqtt => "mqtt",
            TransportKind::Coap => "coap",
            TransportKind::Serial => "serial",
            TransportKind::Can => "can",
            TransportKind::I2c => "i2c",
            TransportKind::Spi => "spi",
            TransportKind::Memory => "memory",
            TransportKind::File => "file",
        }
    }
}

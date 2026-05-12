use crate::TransportError;
use serde::{Deserialize, Serialize};

/// Core FLUX packet carried across all transports.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FluxPacket {
    /// Source room/endpoint
    pub source: String,
    /// Target room/endpoint
    pub target: String,
    /// Payload bytes (serialized FLUX content)
    pub payload: Vec<u8>,
    /// Optional correlation ID for request-response patterns
    pub correlation_id: Option<String>,
    /// Packet priority (0 = highest)
    pub priority: u8,
    /// Timestamp (epoch microseconds)
    pub timestamp: u64,
}

impl FluxPacket {
    pub fn new(source: impl Into<String>, target: impl Into<String>, payload: Vec<u8>) -> Self {
        Self {
            source: source.into(),
            target: target.into(),
            payload,
            correlation_id: None,
            priority: 5,
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_micros() as u64,
        }
    }

    pub fn with_correlation_id(mut self, id: impl Into<String>) -> Self {
        self.correlation_id = Some(id.into());
        self
    }

    pub fn with_priority(mut self, p: u8) -> Self {
        self.priority = p;
        self
    }

    /// Serialize to JSON bytes
    pub fn to_bytes(&self) -> Result<Vec<u8>, TransportError> {
        serde_json::to_vec(self).map_err(|e| TransportError::Serialization(e.to_string()))
    }

    /// Deserialize from JSON bytes
    pub fn from_bytes(data: &[u8]) -> Result<Self, TransportError> {
        serde_json::from_slice(data).map_err(|e| TransportError::Serialization(e.to_string()))
    }
}

/// Metadata describing a transport's capabilities.
#[derive(Debug, Clone)]
pub struct TransportMetadata {
    pub name: &'static str,
    pub latency_us: Option<u64>,
    pub bandwidth_bps: Option<u64>,
    pub reliable: bool,
    pub ordered: bool,
    pub bidirectional: bool,
    pub max_packet_size: Option<usize>,
}

/// The core transport trait. All protocols implement this.
#[async_trait::async_trait]
pub trait Transport: Send + Sync {
    /// Connect to the transport endpoint
    async fn connect(&mut self, config: &crate::TransportConfig) -> Result<(), TransportError>;

    /// Send a FLUX transference packet
    async fn send(&mut self, packet: &FluxPacket) -> Result<(), TransportError>;

    /// Receive a FLUX transference packet
    async fn recv(&mut self) -> Result<FluxPacket, TransportError>;

    /// Check if transport is connected
    fn is_connected(&self) -> bool;

    /// Disconnect gracefully
    async fn disconnect(&mut self) -> Result<(), TransportError>;

    /// Transport metadata (latency estimate, bandwidth, reliability)
    fn metadata(&self) -> TransportMetadata;
}

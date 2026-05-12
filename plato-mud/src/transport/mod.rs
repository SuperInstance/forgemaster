//! PLATO MUD Engine — Transport Adapters
//!
//! Each adapter implements the Transport trait for FLUX transference
//! over different physical/virtual transports.

pub mod memory;

use crate::types::{FluxTransference, TransportConfig};

/// Result type for transport operations
pub type Result<T> = core::result::Result<T, TransportError>;

/// Transport error types
#[derive(Debug)]
pub enum TransportError {
    ConnectionFailed(String),
    SendFailed(String),
    ReceiveFailed(String),
    NotConnected,
    InvalidConfig(String),
}

/// The transport trait — all adapters implement this
pub trait Transport {
    fn connect(&mut self, config: &TransportConfig) -> Result<()>;
    fn send_flux(&mut self, flux: &FluxTransference) -> Result<()>;
    fn recv_flux(&mut self) -> Result<FluxTransference>;
    fn disconnect(&mut self) -> Result<()>;
    fn is_connected(&self) -> bool;
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::transport::memory::MemoryTransport;

    #[test]
    fn test_memory_transport_lifecycle() {
        let config = TransportConfig {
            transport_type: "memory".to_string(),
            address: "local".to_string(),
            port: 0,
            options: Default::default(),
        };

        let mut transport = MemoryTransport::new();
        assert!(!transport.is_connected());

        transport.connect(&config).unwrap();
        assert!(transport.is_connected());

        transport.disconnect().unwrap();
        assert!(!transport.is_connected());
    }
}

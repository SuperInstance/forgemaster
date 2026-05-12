use crate::{FluxPacket, Transport, TransportConfig, TransportError, TransportMetadata};

/// CoAP transport stub for constrained devices.
/// UDP-based, small packets, low-power networks.
pub struct CoapTransport {
    connected: bool,
    endpoint: String,
    pending: Vec<FluxPacket>,
}

impl CoapTransport {
    pub fn new(endpoint: impl Into<String>) -> Self {
        Self {
            connected: false,
            endpoint: endpoint.into(),
            pending: Vec::new(),
        }
    }
}

#[async_trait::async_trait]
impl Transport for CoapTransport {
    async fn connect(&mut self, _config: &TransportConfig) -> Result<(), TransportError> {
        if self.connected {
            return Err(TransportError::AlreadyConnected);
        }
        // CoAP client setup would go here
        self.connected = true;
        Ok(())
    }

    async fn send(&mut self, packet: &FluxPacket) -> Result<(), TransportError> {
        if !self.connected {
            return Err(TransportError::NotConnected);
        }
        tracing::debug!(target = %packet.target, "CoAP send to {}", self.endpoint);
        Ok(())
    }

    async fn recv(&mut self) -> Result<FluxPacket, TransportError> {
        if !self.connected {
            return Err(TransportError::NotConnected);
        }
        if let Some(p) = self.pending.pop() {
            return Ok(p);
        }
        Err(TransportError::RecvFailed("no pending CoAP packets".into()))
    }

    fn is_connected(&self) -> bool {
        self.connected
    }

    async fn disconnect(&mut self) -> Result<(), TransportError> {
        self.connected = false;
        Ok(())
    }

    fn metadata(&self) -> TransportMetadata {
        TransportMetadata {
            name: "coap",
            latency_us: Some(100_000), // ~100ms
            bandwidth_bps: Some(1_000_000),
            reliable: false,
            ordered: false,
            bidirectional: true,
            max_packet_size: Some(1024), // CoAP typically ~1KB
        }
    }
}

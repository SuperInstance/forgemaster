use crate::{FluxPacket, Transport, TransportConfig, TransportError, TransportMetadata};

/// In-process shared-memory channel transport. Zero latency, no serialization.
/// Uses a bounded tokio MPSC channel.
pub struct MemoryTransport {
    tx: Option<tokio::sync::mpsc::Sender<FluxPacket>>,
    rx: Option<tokio::sync::mpsc::Receiver<FluxPacket>>,
    connected: bool,
    buffer_size: usize,
}

impl MemoryTransport {
    pub fn new(buffer_size: usize) -> Self {
        Self {
            tx: None,
            rx: None,
            connected: false,
            buffer_size,
        }
    }

    /// Create a linked pair — packets sent by one can be received by the other.
    pub fn pair(buffer_size: usize) -> (MemoryTransport, MemoryTransport) {
        let (tx1, rx1) = tokio::sync::mpsc::channel(buffer_size);
        let (tx2, rx2) = tokio::sync::mpsc::channel(buffer_size);
        (
            MemoryTransport {
                tx: Some(tx2), // send to the other's rx
                rx: Some(rx1),
                connected: true,
                buffer_size,
            },
            MemoryTransport {
                tx: Some(tx1),
                rx: Some(rx2),
                connected: true,
                buffer_size,
            },
        )
    }
}

#[async_trait::async_trait]
impl Transport for MemoryTransport {
    async fn connect(&mut self, _config: &TransportConfig) -> Result<(), TransportError> {
        if self.connected {
            return Err(TransportError::AlreadyConnected);
        }
        let (tx, rx) = tokio::sync::mpsc::channel(self.buffer_size);
        self.tx = Some(tx);
        self.rx = Some(rx);
        self.connected = true;
        Ok(())
    }

    async fn send(&mut self, packet: &FluxPacket) -> Result<(), TransportError> {
        if !self.connected {
            return Err(TransportError::NotConnected);
        }
        match self.tx.as_ref() {
            Some(tx) => tx.send(packet.clone()).await.map_err(|e| TransportError::SendFailed(e.to_string())),
            None => Err(TransportError::NotConnected),
        }
    }

    async fn recv(&mut self) -> Result<FluxPacket, TransportError> {
        if !self.connected {
            return Err(TransportError::NotConnected);
        }
        match self.rx.as_mut() {
            Some(rx) => rx.recv().await.ok_or(TransportError::RecvFailed("channel closed".into())),
            None => Err(TransportError::NotConnected),
        }
    }

    fn is_connected(&self) -> bool {
        self.connected
    }

    async fn disconnect(&mut self) -> Result<(), TransportError> {
        self.tx = None;
        self.rx = None;
        self.connected = false;
        Ok(())
    }

    fn metadata(&self) -> TransportMetadata {
        TransportMetadata {
            name: "memory",
            latency_us: Some(0),
            bandwidth_bps: Some(u64::MAX),
            reliable: true,
            ordered: true,
            bidirectional: true,
            max_packet_size: None,
        }
    }
}

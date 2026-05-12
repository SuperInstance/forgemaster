use crate::{FluxPacket, Transport, TransportConfig, TransportError, TransportMetadata};
use std::collections::HashMap;

/// TCP transport with optional TLS support.
/// Reliable, ordered, bidirectional. For server-to-server, dashboards, fleet backbone.
pub struct TcpTransport {
    stream: Option<tokio::net::TcpStream>,
    connected: bool,
    addr: String,
    use_tls: bool,
}

impl TcpTransport {
    pub fn new(addr: impl Into<String>) -> Self {
        Self {
            stream: None,
            connected: false,
            addr: addr.into(),
            use_tls: false,
        }
    }

    pub fn with_tls(mut self) -> Self {
        self.use_tls = true;
        self
    }
}

#[async_trait::async_trait]
impl Transport for TcpTransport {
    async fn connect(&mut self, config: &TransportConfig) -> Result<(), TransportError> {
        if self.connected {
            return Err(TransportError::AlreadyConnected);
        }
        // Allow override from config settings
        let settings = config.get("tcp").map(|e| e.settings.clone()).unwrap_or_default();
        let addr = settings.get("addr").map(|s| s.as_str()).unwrap_or(&self.addr);
        
        let stream = tokio::net::TcpStream::connect(addr).await
            .map_err(|e| TransportError::ConnectionFailed(e.to_string()))?;
        
        // TODO: TLS handshake when use_tls is true (requires tokio-rustls)
        
        self.stream = Some(stream);
        self.connected = true;
        Ok(())
    }

    async fn send(&mut self, packet: &FluxPacket) -> Result<(), TransportError> {
        if !self.connected {
            return Err(TransportError::NotConnected);
        }
        match self.stream.as_mut() {
            Some(stream) => {
                use tokio::io::AsyncWriteExt;
                let data = packet.to_bytes()?;
                let len = data.len() as u32;
                // Frame: 4-byte length prefix + payload
                stream.write_all(&len.to_be_bytes()).await?;
                stream.write_all(&data).await?;
                Ok(())
            }
            None => Err(TransportError::NotConnected),
        }
    }

    async fn recv(&mut self) -> Result<FluxPacket, TransportError> {
        if !self.connected {
            return Err(TransportError::NotConnected);
        }
        match self.stream.as_mut() {
            Some(stream) => {
                use tokio::io::AsyncReadExt;
                let mut len_buf = [0u8; 4];
                stream.read_exact(&mut len_buf).await?;
                let len = u32::from_be_bytes(len_buf) as usize;
                let mut data = vec![0u8; len];
                stream.read_exact(&mut data).await?;
                FluxPacket::from_bytes(&data)
            }
            None => Err(TransportError::NotConnected),
        }
    }

    fn is_connected(&self) -> bool {
        self.connected
    }

    async fn disconnect(&mut self) -> Result<(), TransportError> {
        if let Some(stream) = self.stream.take() {
            use tokio::io::AsyncWriteExt;
            let _ = stream.shutdown().await;
        }
        self.connected = false;
        Ok(())
    }

    fn metadata(&self) -> TransportMetadata {
        TransportMetadata {
            name: "tcp",
            latency_us: Some(100), // ~100μs LAN
            bandwidth_bps: Some(1_000_000_000), // ~1Gbps
            reliable: true,
            ordered: true,
            bidirectional: true,
            max_packet_size: None,
        }
    }
}

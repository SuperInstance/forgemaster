use crate::{FluxPacket, Transport, TransportConfig, TransportError, TransportMetadata};

/// HTTP/REST transport.
/// Request-response, stateless. For API endpoints, third-party integration, webhooks.
///
/// This implementation uses a simple TCP-based HTTP client to avoid complex hyper API surface.
/// In production, swap in reqwest or a full hyper implementation.
pub struct HttpTransport {
    connected: bool,
    endpoint: String,
    pending: Vec<FluxPacket>,
}

impl HttpTransport {
    pub fn new(endpoint: impl Into<String>) -> Self {
        Self {
            connected: false,
            endpoint: endpoint.into(),
            pending: Vec::new(),
        }
    }

    fn parse_host_port(&self) -> (&str, u16) {
        let url = self
            .endpoint
            .trim_start_matches("http://")
            .trim_start_matches("https://");
        let host_port = url.split('/').next().unwrap_or("127.0.0.1:80");
        let mut parts = host_port.split(':');
        let host = parts.next().unwrap_or("127.0.0.1");
        let port: u16 = parts.next().and_then(|p| p.parse().ok()).unwrap_or(80);
        (host, port)
    }
}

#[async_trait::async_trait]
impl Transport for HttpTransport {
    async fn connect(&mut self, _config: &TransportConfig) -> Result<(), TransportError> {
        if self.connected {
            return Err(TransportError::AlreadyConnected);
        }
        self.connected = true;
        Ok(())
    }

    async fn send(&mut self, packet: &FluxPacket) -> Result<(), TransportError> {
        if !self.connected {
            return Err(TransportError::NotConnected);
        }
        let data = packet.to_bytes()?;
        let (host, port) = self.parse_host_port();
        let addr = format!("{}:{}", host, port);

        let mut stream = tokio::net::TcpStream::connect(&addr).await?;

        use tokio::io::AsyncWriteExt;
        let request = format!(
            "POST /flux HTTP/1.1\r\nHost: {}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n",
            host,
            data.len()
        );
        stream.write_all(request.as_bytes()).await?;
        stream.write_all(&data).await?;

        // Read response (discard for now)
        use tokio::io::AsyncReadExt;
        let mut buf = vec![0u8; 1024];
        let _ = stream.read(&mut buf).await;

        Ok(())
    }

    async fn recv(&mut self) -> Result<FluxPacket, TransportError> {
        if !self.connected {
            return Err(TransportError::NotConnected);
        }
        if let Some(packet) = self.pending.pop() {
            return Ok(packet);
        }
        tokio::time::sleep(std::time::Duration::from_millis(100)).await;
        Err(TransportError::RecvFailed("no pending packets".into()))
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
            name: "http",
            latency_us: Some(1_000),
            bandwidth_bps: Some(100_000_000),
            reliable: true,
            ordered: false,
            bidirectional: false,
            max_packet_size: None,
        }
    }
}

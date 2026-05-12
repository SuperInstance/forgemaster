use crate::{FluxPacket, Transport, TransportConfig, TransportError, TransportMetadata};
use std::path::PathBuf;

/// File-based transport. Watches a directory for `.flux` files.
/// Unidirectional (read from watched dir), durable, great for air-gapped systems.
pub struct FileTransport {
    watch_dir: PathBuf,
    connected: bool,
}

impl FileTransport {
    pub fn new(watch_dir: impl Into<PathBuf>) -> Self {
        Self {
            watch_dir: watch_dir.into(),
            connected: false,
        }
    }
}

#[async_trait::async_trait]
impl Transport for FileTransport {
    async fn connect(&mut self, _config: &TransportConfig) -> Result<(), TransportError> {
        if self.connected {
            return Err(TransportError::AlreadyConnected);
        }
        tokio::fs::create_dir_all(&self.watch_dir).await?;
        self.connected = true;
        Ok(())
    }

    async fn send(&mut self, packet: &FluxPacket) -> Result<(), TransportError> {
        if !self.connected {
            return Err(TransportError::NotConnected);
        }
        let filename = format!(
            "{:020}_{}.flux",
            packet.timestamp, packet.target
        );
        let path = self.watch_dir.join(&filename);
        let data = packet.to_bytes()?;
        tokio::fs::write(&path, &data).await?;
        Ok(())
    }

    async fn recv(&mut self) -> Result<FluxPacket, TransportError> {
        if !self.connected {
            return Err(TransportError::NotConnected);
        }
        loop {
            let mut entries = tokio::fs::read_dir(&self.watch_dir).await?;
            let mut files = Vec::new();
            while let Some(entry) = entries.next_entry().await? {
                let path = entry.path();
                if path.extension().map_or(false, |e| e == "flux") {
                    files.push(path);
                }
            }
            files.sort();
            if let Some(path) = files.first() {
                let data = tokio::fs::read(&path).await?;
                let packet = FluxPacket::from_bytes(&data)?;
                // Remove file after reading
                let _ = tokio::fs::remove_file(&path).await;
                return Ok(packet);
            }
            tokio::time::sleep(std::time::Duration::from_millis(50)).await;
        }
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
            name: "file",
            latency_us: Some(100_000), // ~100ms filesystem poll
            bandwidth_bps: Some(1_000_000),
            reliable: true,
            ordered: false,
            bidirectional: false,
            max_packet_size: None,
        }
    }
}

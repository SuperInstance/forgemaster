use crate::{FluxPacket, Transport, TransportConfig, TransportError, TransportMetadata};

/// SPI transport (linux-embedded-hal).
/// For high-speed sensor reading, displays, ADC. Full-duplex, clocked.
pub struct SpiTransport {
    connected: bool,
    device: String,
    speed_hz: u32,
    buffer: Vec<FluxPacket>,
}

impl SpiTransport {
    pub fn new(device: impl Into<String>, speed_hz: u32) -> Self {
        Self {
            connected: false,
            device: device.into(),
            speed_hz,
            buffer: Vec::new(),
        }
    }

    pub fn default_speed() -> u32 {
        1_000_000 // 1 MHz
    }
}

#[async_trait::async_trait]
impl Transport for SpiTransport {
    async fn connect(&mut self, _config: &TransportConfig) -> Result<(), TransportError> {
        if self.connected {
            return Err(TransportError::AlreadyConnected);
        }
        // Real: open /dev/spidevX.Y via linux-embedded-hal
        tracing::info!(device = %self.device, speed = self.speed_hz, "SPI connect (mock)");
        self.connected = true;
        Ok(())
    }

    async fn send(&mut self, packet: &FluxPacket) -> Result<(), TransportError> {
        if !self.connected {
            return Err(TransportError::NotConnected);
        }
        let data = packet.to_bytes()?;
        tracing::debug!(device = %self.device, len = data.len(), "SPI transfer");
        Ok(())
    }

    async fn recv(&mut self) -> Result<FluxPacket, TransportError> {
        if !self.connected {
            return Err(TransportError::NotConnected);
        }
        if let Some(p) = self.buffer.pop() {
            return Ok(p);
        }
        Err(TransportError::RecvFailed("no SPI data available".into()))
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
            name: "spi",
            latency_us: Some(10), // ~10μs
            bandwidth_bps: Some(50_000_000), // SPI can go very fast
            reliable: true,
            ordered: true,
            bidirectional: true,
            max_packet_size: Some(256),
        }
    }
}

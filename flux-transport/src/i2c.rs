use crate::{FluxPacket, Transport, TransportConfig, TransportError, TransportMetadata};

/// I2C transport (linux-embedded-hal).
/// For sensor reading, EEPROM, low-speed peripherals. Master-slave, addressed.
pub struct I2cTransport {
    connected: bool,
    bus: u8,
    address: u8,
    buffer: Vec<FluxPacket>,
}

impl I2cTransport {
    pub fn new(bus: u8, address: u8) -> Self {
        Self {
            connected: false,
            bus,
            address,
            buffer: Vec::new(),
        }
    }
}

#[async_trait::async_trait]
impl Transport for I2cTransport {
    async fn connect(&mut self, _config: &TransportConfig) -> Result<(), TransportError> {
        if self.connected {
            return Err(TransportError::AlreadyConnected);
        }
        // In a real implementation, open /dev/i2c-{bus} via linux-embedded-hal
        // For now, mock mode
        self.connected = true;
        Ok(())
    }

    async fn send(&mut self, packet: &FluxPacket) -> Result<(), TransportError> {
        if !self.connected {
            return Err(TransportError::NotConnected);
        }
        let data = packet.to_bytes()?;
        // I2C write: address + register + data
        tracing::debug!(
            bus = self.bus,
            addr = self.address,
            len = data.len(),
            "I2C write"
        );
        Ok(())
    }

    async fn recv(&mut self) -> Result<FluxPacket, TransportError> {
        if !self.connected {
            return Err(TransportError::NotConnected);
        }
        if let Some(p) = self.buffer.pop() {
            return Ok(p);
        }
        Err(TransportError::RecvFailed("no I2C data available".into()))
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
            name: "i2c",
            latency_us: Some(100), // ~100μs
            bandwidth_bps: Some(3_400_000), // I2C fast-mode = 3.4Mbps
            reliable: true,
            ordered: true,
            bidirectional: true,
            max_packet_size: Some(32), // Small payloads typical
        }
    }
}

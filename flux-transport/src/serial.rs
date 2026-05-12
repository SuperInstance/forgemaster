use crate::{FluxPacket, Transport, TransportConfig, TransportError, TransportMetadata};

/// Serial/UART transport using serialport.
/// For embedded debug, GPS, direct device connection.
pub struct SerialTransport {
    port: Option<Box<dyn serialport::SerialPort>>,
    connected: bool,
    port_name: String,
    baud_rate: u32,
}

impl SerialTransport {
    pub fn new(port_name: impl Into<String>, baud_rate: u32) -> Self {
        Self {
            port: None,
            connected: false,
            port_name: port_name.into(),
            baud_rate,
        }
    }

    pub fn default_baud() -> u32 {
        115_200
    }
}

#[async_trait::async_trait]
impl Transport for SerialTransport {
    async fn connect(&mut self, _config: &TransportConfig) -> Result<(), TransportError> {
        if self.connected {
            return Err(TransportError::AlreadyConnected);
        }
        let port = serialport::new(&self.port_name, self.baud_rate)
            .timeout(std::time::Duration::from_secs(5))
            .open()
            .map_err(|e| TransportError::ConnectionFailed(e.to_string()))?;
        self.port = Some(port);
        self.connected = true;
        Ok(())
    }

    async fn send(&mut self, packet: &FluxPacket) -> Result<(), TransportError> {
        if !self.connected {
            return Err(TransportError::NotConnected);
        }
        let port = self.port.as_mut().ok_or(TransportError::NotConnected)?;
        let data = packet.to_bytes()?;
        // Frame with newline delimiter
        let mut framed = data;
        framed.push(b'\n');
        port.write_all(&framed)
            .map_err(|e| TransportError::SendFailed(e.to_string()))
    }

    async fn recv(&mut self) -> Result<FluxPacket, TransportError> {
        if !self.connected {
            return Err(TransportError::NotConnected);
        }
        let port = self.port.as_mut().ok_or(TransportError::NotConnected)?;
        let mut buf = Vec::new();
        let mut byte = [0u8; 1];
        loop {
            match port.read(&mut byte) {
                Ok(1) => {
                    if byte[0] == b'\n' {
                        break;
                    }
                    buf.push(byte[0]);
                }
                Ok(_) => continue,
                Err(ref e) if e.kind() == std::io::ErrorKind::TimedOut => {
                    tokio::time::sleep(std::time::Duration::from_millis(10)).await;
                    continue;
                }
                Err(e) => return Err(TransportError::RecvFailed(e.to_string())),
            }
        }
        FluxPacket::from_bytes(&buf)
    }

    fn is_connected(&self) -> bool {
        self.connected
    }

    async fn disconnect(&mut self) -> Result<(), TransportError> {
        self.port = None;
        self.connected = false;
        Ok(())
    }

    fn metadata(&self) -> TransportMetadata {
        TransportMetadata {
            name: "serial",
            latency_us: Some(1_000), // ~1ms at 115200 baud
            bandwidth_bps: Some(11_520), // 115200 baud / 10 bits/byte
            reliable: true,
            ordered: true,
            bidirectional: true,
            max_packet_size: Some(1024),
        }
    }
}

// Need Read/Write imports for serialport
use std::io::{Read, Write};

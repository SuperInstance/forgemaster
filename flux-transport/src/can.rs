use crate::{FluxPacket, Transport, TransportConfig, TransportError, TransportMetadata};

/// CAN bus transport (socketcan on Linux, stub otherwise).
/// For automotive, industrial automation, robotics.
pub struct CanTransport {
    socket: Option<socketcan::AsyncCanSocket>,
    connected: bool,
    interface: String,
}

impl CanTransport {
    pub fn new(interface: impl Into<String>) -> Self {
        Self {
            socket: None,
            connected: false,
            interface: interface.into(),
        }
    }
}

#[async_trait::async_trait]
impl Transport for CanTransport {
    async fn connect(&mut self, _config: &TransportConfig) -> Result<(), TransportError> {
        if self.connected {
            return Err(TransportError::AlreadyConnected);
        }
        let sock = socketcan::CanSocket::open(&self.interface)
            .map_err(|e| TransportError::ConnectionFailed(e.to_string()))?;
        let async_sock = socketcan::AsyncCanSocket::new(sock)
            .map_err(|e| TransportError::ConnectionFailed(e.to_string()))?;
        self.socket = Some(async_sock);
        self.connected = true;
        Ok(())
    }

    async fn send(&mut self, packet: &FluxPacket) -> Result<(), TransportError> {
        if !self.connected {
            return Err(TransportError::NotConnected);
        }
        let sock = self.socket.as_mut().ok_or(TransportError::NotConnected)?;
        let data = packet.to_bytes()?;
        // CAN frames are max 8 bytes (classic) or 64 bytes (FD)
        // Split packet into multiple frames if needed
        for (i, chunk) in data.chunks(8).enumerate() {
            let mut frame_data = [0u8; 8];
            frame_data[..chunk.len()].copy_from_slice(chunk);
            let frame = socketcan::CanFrame::new(
                (0x100 + i) as socketcan::CanId,
                &frame_data[..chunk.len()],
            ).map_err(|e| TransportError::SendFailed(format!("{:?}", e)))?;
            sock.write_frame(&frame).await
                .map_err(|e| TransportError::SendFailed(e.to_string()))?;
        }
        Ok(())
    }

    async fn recv(&mut self) -> Result<FluxPacket, TransportError> {
        if !self.connected {
            return Err(TransportError::NotConnected);
        }
        let sock = self.socket.as_mut().ok_or(TransportError::NotConnected)?;
        let frame = sock.read_frame().await
            .map_err(|e| TransportError::RecvFailed(e.to_string()))?;
        // Simplified: single-frame receive
        FluxPacket::from_bytes(frame.data())
    }

    fn is_connected(&self) -> bool {
        self.connected
    }

    async fn disconnect(&mut self) -> Result<(), TransportError> {
        self.socket = None;
        self.connected = false;
        Ok(())
    }

    fn metadata(&self) -> TransportMetadata {
        TransportMetadata {
            name: "can",
            latency_us: Some(1_000), // ~1ms
            bandwidth_bps: Some(1_000_000), // CAN 2.0B = 1Mbps
            reliable: false,
            ordered: false,
            bidirectional: true,
            max_packet_size: Some(8), // Classic CAN
        }
    }
}

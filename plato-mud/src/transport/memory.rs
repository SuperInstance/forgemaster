//! PLATO MUD Engine — Shared Memory Transport
//!
//! Multi-process on same host. In-process channel for now.

extern crate alloc;

use alloc::collections::VecDeque;
use alloc::string::String;

use crate::transport::{Result, Transport, TransportError};
use crate::types::{FluxTransference, TransportConfig};

/// Shared memory transport — uses an in-process queue
pub struct MemoryTransport {
    connected: bool,
    inbox: VecDeque<FluxTransference>,
    // In a real implementation, this would use shared memory segments
    // or Unix domain sockets for multi-process communication
}

impl Default for MemoryTransport {
    fn default() -> Self {
        Self::new()
    }
}

impl MemoryTransport {
    pub fn new() -> Self {
        Self {
            connected: false,
            inbox: VecDeque::new(),
        }
    }

    /// Inject a flux into the inbox (simulating reception from another process)
    pub fn inject(&mut self, flux: FluxTransference) {
        self.inbox.push_back(flux);
    }
}

impl Transport for MemoryTransport {
    fn connect(&mut self, _config: &TransportConfig) -> Result<()> {
        self.connected = true;
        Ok(())
    }

    fn send_flux(&mut self, _flux: &FluxTransference) -> Result<()> {
        if !self.connected {
            return Err(TransportError::NotConnected);
        }
        // In shared memory, "send" means write to shared segment
        // For now, we just acknowledge the send
        Ok(())
    }

    fn recv_flux(&mut self) -> Result<FluxTransference> {
        if !self.connected {
            return Err(TransportError::NotConnected);
        }
        self.inbox
            .pop_front()
            .ok_or(TransportError::ReceiveFailed(String::from(
                "No pending flux",
            )))
    }

    fn disconnect(&mut self) -> Result<()> {
        self.connected = false;
        self.inbox.clear();
        Ok(())
    }

    fn is_connected(&self) -> bool {
        self.connected
    }
}

// ─── Stub transports for std feature ────────────────────────────────────────
// TCP, WebSocket, MQTT, Serial, CAN adapters are stub implementations
// that compile under the std feature but don't require actual hardware.

#[cfg(feature = "std")]
pub mod tcp {
    use crate::transport::{Result, Transport, TransportError};
    use crate::types::{FluxTransference, TransportConfig};

    /// TCP transport adapter (enterprise, LAN)
    pub struct TcpTransport {
        connected: bool,
        address: String,
        port: u16,
    }

    impl Default for TcpTransport {
        fn default() -> Self {
            Self::new()
        }
    }

    impl TcpTransport {
        pub fn new() -> Self {
            Self {
                connected: false,
                address: String::new(),
                port: 0,
            }
        }
    }

    impl Transport for TcpTransport {
        fn connect(&mut self, config: &TransportConfig) -> Result<()> {
            self.address = config.address.clone();
            self.port = config.port;
            // In a real implementation: TcpStream::connect()
            self.connected = true;
            Ok(())
        }

        fn send_flux(&mut self, _flux: &FluxTransference) -> Result<()> {
            if !self.connected {
                return Err(TransportError::NotConnected);
            }
            // In a real implementation: serialize and write to TcpStream
            Ok(())
        }

        fn recv_flux(&mut self) -> Result<FluxTransference> {
            if !self.connected {
                return Err(TransportError::NotConnected);
            }
            Err(TransportError::ReceiveFailed(
                "TCP recv not yet implemented".into(),
            ))
        }

        fn disconnect(&mut self) -> Result<()> {
            self.connected = false;
            Ok(())
        }

        fn is_connected(&self) -> bool {
            self.connected
        }
    }
}

#[cfg(feature = "std")]
pub mod websocket {
    use crate::transport::{Result, Transport, TransportError};
    use crate::types::{FluxTransference, TransportConfig};

    /// WebSocket transport adapter (browser dashboard)
    pub struct WebSocketTransport {
        connected: bool,
    }

    impl Default for WebSocketTransport {
        fn default() -> Self {
            Self::new()
        }
    }

    impl WebSocketTransport {
        pub fn new() -> Self {
            Self { connected: false }
        }
    }

    impl Transport for WebSocketTransport {
        fn connect(&mut self, _config: &TransportConfig) -> Result<()> {
            self.connected = true;
            Ok(())
        }
        fn send_flux(&mut self, _flux: &FluxTransference) -> Result<()> {
            if !self.connected {
                return Err(TransportError::NotConnected);
            }
            Ok(())
        }
        fn recv_flux(&mut self) -> Result<FluxTransference> {
            if !self.connected {
                return Err(TransportError::NotConnected);
            }
            Err(TransportError::ReceiveFailed(
                "WebSocket recv not yet implemented".into(),
            ))
        }
        fn disconnect(&mut self) -> Result<()> {
            self.connected = false;
            Ok(())
        }
        fn is_connected(&self) -> bool {
            self.connected
        }
    }
}

#[cfg(feature = "std")]
pub mod mqtt {
    use crate::transport::{Result, Transport, TransportError};
    use crate::types::{FluxTransference, TransportConfig};

    /// MQTT transport adapter (IoT, cloud)
    pub struct MqttTransport {
        connected: bool,
        topic: String,
    }

    impl Default for MqttTransport {
        fn default() -> Self {
            Self::new()
        }
    }

    impl MqttTransport {
        pub fn new() -> Self {
            Self {
                connected: false,
                topic: String::new(),
            }
        }
    }

    impl Transport for MqttTransport {
        fn connect(&mut self, config: &TransportConfig) -> Result<()> {
            self.topic = config.options.get("topic").cloned().unwrap_or_default();
            self.connected = true;
            Ok(())
        }
        fn send_flux(&mut self, _flux: &FluxTransference) -> Result<()> {
            if !self.connected {
                return Err(TransportError::NotConnected);
            }
            Ok(())
        }
        fn recv_flux(&mut self) -> Result<FluxTransference> {
            if !self.connected {
                return Err(TransportError::NotConnected);
            }
            Err(TransportError::ReceiveFailed(
                "MQTT recv not yet implemented".into(),
            ))
        }
        fn disconnect(&mut self) -> Result<()> {
            self.connected = false;
            Ok(())
        }
        fn is_connected(&self) -> bool {
            self.connected
        }
    }
}

#[cfg(feature = "std")]
pub mod serial {
    use crate::transport::{Result, Transport, TransportError};
    use crate::types::{FluxTransference, TransportConfig};

    /// Serial/UART transport adapter (embedded, debug)
    pub struct SerialTransport {
        connected: bool,
        port_name: String,
        baud_rate: u32,
    }

    impl Default for SerialTransport {
        fn default() -> Self {
            Self::new()
        }
    }

    impl SerialTransport {
        pub fn new() -> Self {
            Self {
                connected: false,
                port_name: String::new(),
                baud_rate: 115200,
            }
        }
    }

    impl Transport for SerialTransport {
        fn connect(&mut self, config: &TransportConfig) -> Result<()> {
            self.port_name = config.address.clone();
            self.baud_rate = config
                .options
                .get("baud")
                .and_then(|b| b.parse().ok())
                .unwrap_or(115200);
            self.connected = true;
            Ok(())
        }
        fn send_flux(&mut self, _flux: &FluxTransference) -> Result<()> {
            if !self.connected {
                return Err(TransportError::NotConnected);
            }
            Ok(())
        }
        fn recv_flux(&mut self) -> Result<FluxTransference> {
            if !self.connected {
                return Err(TransportError::NotConnected);
            }
            Err(TransportError::ReceiveFailed(
                "Serial recv not yet implemented".into(),
            ))
        }
        fn disconnect(&mut self) -> Result<()> {
            self.connected = false;
            Ok(())
        }
        fn is_connected(&self) -> bool {
            self.connected
        }
    }
}

#[cfg(feature = "std")]
pub mod can_bus {
    use crate::transport::{Result, Transport, TransportError};
    use crate::types::{FluxTransference, TransportConfig};

    /// CAN bus transport adapter (automotive, industrial)
    pub struct CanTransport {
        connected: bool,
        interface: String,
    }

    impl Default for CanTransport {
        fn default() -> Self {
            Self::new()
        }
    }

    impl CanTransport {
        pub fn new() -> Self {
            Self {
                connected: false,
                interface: String::new(),
            }
        }
    }

    impl Transport for CanTransport {
        fn connect(&mut self, config: &TransportConfig) -> Result<()> {
            self.interface = config.address.clone();
            self.connected = true;
            Ok(())
        }
        fn send_flux(&mut self, _flux: &FluxTransference) -> Result<()> {
            if !self.connected {
                return Err(TransportError::NotConnected);
            }
            Ok(())
        }
        fn recv_flux(&mut self) -> Result<FluxTransference> {
            if !self.connected {
                return Err(TransportError::NotConnected);
            }
            Err(TransportError::ReceiveFailed(
                "CAN recv not yet implemented".into(),
            ))
        }
        fn disconnect(&mut self) -> Result<()> {
            self.connected = false;
            Ok(())
        }
        fn is_connected(&self) -> bool {
            self.connected
        }
    }
}

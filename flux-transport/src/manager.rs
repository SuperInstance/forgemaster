use crate::{FluxPacket, Transport, TransportConfig, TransportError, TransportMetadata, TransportKind};
use std::collections::HashMap;

/// Route rule: target pattern -> transport name
#[derive(Debug, Clone)]
pub struct Route {
    /// Target room prefix to match (e.g. "sensor/*", "dashboard")
    pub target_pattern: String,
    /// Transport name to route to
    pub transport_name: String,
}

/// Manages multiple transports and routes FLUX packets to the right one.
pub struct TransportManager {
    transports: HashMap<String, Box<dyn Transport>>,
    routes: Vec<Route>,
}

impl TransportManager {
    pub fn new() -> Self {
        Self {
            transports: HashMap::new(),
            routes: Vec::new(),
        }
    }

    /// Route a FLUX packet to the right transport based on target room.
    pub async fn route(&mut self, packet: &FluxPacket) -> Result<(), TransportError> {
        let transport_name = self.resolve_route(&packet.target)?;
        let transport = self.transports
            .get_mut(&transport_name)
            .ok_or_else(|| TransportError::NotFound(transport_name))?;
        transport.send(packet).await
    }

    /// Register a new transport.
    pub fn register(&mut self, name: &str, transport: Box<dyn Transport>) {
        self.transports.insert(name.to_string(), transport);
    }

    /// Add a routing rule.
    pub fn add_route(&mut self, target_pattern: impl Into<String>, transport_name: impl Into<String>) {
        self.routes.push(Route {
            target_pattern: target_pattern.into(),
            transport_name: transport_name.into(),
        });
    }

    /// Resolve a target to a transport name.
    fn resolve_route(&self, target: &str) -> Result<String, TransportError> {
        // Exact match first
        for route in &self.routes {
            if route.target_pattern == target {
                return Ok(route.transport_name.clone());
            }
        }
        // Prefix/wildcard match
        for route in &self.routes {
            let pattern = &route.target_pattern;
            if pattern.ends_with("/*") {
                let prefix = &pattern[..pattern.len() - 2];
                if target.starts_with(prefix) {
                    return Ok(route.transport_name.clone());
                }
            } else if pattern == "*" {
                return Ok(route.transport_name.clone());
            }
        }
        // Fallback: use first transport
        self.transports
            .keys()
            .next()
            .cloned()
            .ok_or(TransportError::NotFound("no transports registered".into()))
    }

    /// Auto-discover available transports on this system.
    pub async fn discover(&mut self) -> Vec<TransportMetadata> {
        let mut found = Vec::new();

        // Always available
        found.push(TransportMetadata {
            name: "memory",
            latency_us: Some(0),
            bandwidth_bps: Some(u64::MAX),
            reliable: true,
            ordered: true,
            bidirectional: true,
            max_packet_size: None,
        });

        // Check for serial ports
        #[cfg(feature = "serial")]
        {
            if let Ok(ports) = serialport::available_ports() {
                for port in &ports {
                    tracing::info!(port = %port.port_name, "discovered serial port");
                }
                if !ports.is_empty() {
                    found.push(TransportMetadata {
                        name: "serial",
                        latency_us: Some(1_000),
                        bandwidth_bps: Some(11_520),
                        reliable: true,
                        ordered: true,
                        bidirectional: true,
                        max_packet_size: Some(1024),
                    });
                }
            }
        }

        // Check for CAN interfaces (Linux)
        #[cfg(target_os = "linux")]
        {
            let can_ifaces = ["can0", "vcan0", "can1"];
            for iface in &can_ifaces {
                if std::path::Path::new(&format!("/sys/class/net/{}", iface)).exists() {
                    tracing::info!(interface = iface, "discovered CAN interface");
                    found.push(TransportMetadata {
                        name: "can",
                        latency_us: Some(1_000),
                        bandwidth_bps: Some(1_000_000),
                        reliable: false,
                        ordered: false,
                        bidirectional: true,
                        max_packet_size: Some(8),
                    });
                    break;
                }
            }
        }

        // Check for I2C buses
        #[cfg(target_os = "linux")]
        {
            for i in 0..10u8 {
                let path = format!("/dev/i2c-{}", i);
                if std::path::Path::new(&path).exists() {
                    tracing::info!(bus = i, "discovered I2C bus");
                    found.push(TransportMetadata {
                        name: "i2c",
                        latency_us: Some(100),
                        bandwidth_bps: Some(3_400_000),
                        reliable: true,
                        ordered: true,
                        bidirectional: true,
                        max_packet_size: Some(32),
                    });
                    break;
                }
            }
        }

        // Check for SPI devices
        #[cfg(target_os = "linux")]
        {
            for i in 0..10u8 {
                for j in 0..10u8 {
                    let path = format!("/dev/spidev{}.{}", i, j);
                    if std::path::Path::new(&path).exists() {
                        tracing::info!(device = path, "discovered SPI device");
                        found.push(TransportMetadata {
                            name: "spi",
                            latency_us: Some(10),
                            bandwidth_bps: Some(50_000_000),
                            reliable: true,
                            ordered: true,
                            bidirectional: true,
                            max_packet_size: Some(256),
                        });
                        break;
                    }
                }
            }
        }

        found
    }

    /// Health check all transports.
    pub async fn health_check(&self) -> HashMap<String, bool> {
        let mut results = HashMap::new();
        for (name, transport) in &self.transports {
            results.insert(name.clone(), transport.is_connected());
        }
        results
    }

    /// Get metadata for all registered transports.
    pub fn all_metadata(&self) -> Vec<(&str, TransportMetadata)> {
        self.transports
            .iter()
            .map(|(name, t)| (name.as_str(), t.metadata()))
            .collect()
    }

    /// Get a transport by name.
    pub fn get(&self, name: &str) -> Option<&dyn Transport> {
        self.transports.get(name).map(|t| t.as_ref())
    }

    /// Get a mutable transport by name.
    pub fn get_mut(&mut self, name: &str) -> Option<&mut Box<dyn Transport>> {
        self.transports.get_mut(name)
    }
}

impl Default for TransportManager {
    fn default() -> Self {
        Self::new()
    }
}

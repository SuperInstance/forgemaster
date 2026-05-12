//! FLUX Transport Layer — multi-protocol adapters for enterprise, IoT, and everything in between.

mod types;
mod error;
mod config;

pub use types::*;
pub use error::*;
pub use config::*;

// Transport implementations behind feature flags
#[cfg(feature = "memory")]
pub mod memory;
#[cfg(feature = "file")]
pub mod file;
#[cfg(feature = "tcp")]
pub mod tcp;
#[cfg(feature = "websocket")]
pub mod websocket;
#[cfg(feature = "http")]
pub mod http;
#[cfg(feature = "grpc")]
pub mod grpc;
#[cfg(feature = "mqtt")]
pub mod mqtt;
#[cfg(feature = "coap")]
pub mod coap;
#[cfg(feature = "serial")]
pub mod serial;
#[cfg(feature = "can")]
pub mod can;
#[cfg(feature = "i2c")]
pub mod i2c;
#[cfg(feature = "spi")]
pub mod spi;

pub mod manager;

pub mod prelude {
    pub use crate::{Transport, TransportConfig, TransportError, TransportMetadata, FluxPacket, TransportKind};
}

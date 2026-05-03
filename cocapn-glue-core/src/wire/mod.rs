//! Wire protocol types — TierId, WireMessage, transport traits, serialization.

mod addr;
mod message;
mod serde;
mod transport;

pub use addr::TierId;
pub use message::{WireMessage, WireError, DataChunk, Handshake, Ack};
pub use transport::Transport;
#[cfg(feature = "async")]
pub use transport::AsyncTransport;
pub use serde::{serialize_message, deserialize_message};

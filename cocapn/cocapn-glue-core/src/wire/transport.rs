//! Blocking and async transport traits.

use crate::wire::WireMessage;

/// Blocking transport trait. Implementations provide a read/write pair.
pub trait Transport {
    type Error;
    fn send(&mut self, msg: &WireMessage) -> Result<(), Self::Error>;
    fn recv(&mut self) -> Result<WireMessage, Self::Error>;
}

/// Async transport trait (requires `async` feature).
#[cfg(feature = "async")]
#[async_trait::async_trait]
pub trait AsyncTransport {
    type Error;
    async fn send(&mut self, msg: &WireMessage) -> Result<(), Self::Error>;
    async fn recv(&mut self) -> Result<WireMessage, Self::Error>;
}

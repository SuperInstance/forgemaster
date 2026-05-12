use thiserror::Error;

#[derive(Debug, Error)]
pub enum TransportError {
    #[error("Connection failed: {0}")]
    ConnectionFailed(String),

    #[error("Not connected")]
    NotConnected,

    #[error("Already connected")]
    AlreadyConnected,

    #[error("Send failed: {0}")]
    SendFailed(String),

    #[error("Receive failed: {0}")]
    RecvFailed(String),

    #[error("Disconnect failed: {0}")]
    DisconnectFailed(String),

    #[error("Timeout")]
    Timeout,

    #[error("Serialization error: {0}")]
    Serialization(String),

    #[error("Configuration error: {0}")]
    Config(String),

    #[error("Transport not found: {0}")]
    NotFound(String),

    #[error("Discovery failed: {0}")]
    DiscoveryFailed(String),

    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),

    #[error("{0}")]
    Other(String),
}

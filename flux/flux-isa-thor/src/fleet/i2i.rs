use serde::{Deserialize, Serialize};
use std::fmt;

/// I2I (Instance-to-Instance) message types for fleet coordination.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum I2iType {
    /// Task assignment
    Task,
    /// Status update / heartbeat
    Status,
    /// Checkpoint — intermediate progress
    Checkpoint,
    /// Blocker — need help or input
    Blocker,
    /// Deliverable — completed work product
    Deliverable,
}

impl fmt::Display for I2iType {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            I2iType::Task => write!(f, "TASK"),
            I2iType::Status => write!(f, "STATUS"),
            I2iType::Checkpoint => write!(f, "CHECKPOINT"),
            I2iType::Blocker => write!(f, "BLOCKER"),
            I2iType::Deliverable => write!(f, "DELIVERABLE"),
        }
    }
}

/// An I2I message exchanged between fleet nodes.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct I2iMessage {
    pub msg_type: I2iType,
    pub from: String,
    pub payload: Vec<u8>,
    pub timestamp: u64,
}

impl I2iMessage {
    /// Create a new I2I message.
    pub fn new(msg_type: I2iType, from: &str, payload: Vec<u8>) -> Self {
        Self {
            msg_type,
            from: from.to_string(),
            payload,
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs(),
        }
    }

    /// Parse payload as JSON.
    pub fn payload_json<T: serde::de::DeserializeOwned>(&self) -> Result<T, serde_json::Error> {
        serde_json::from_slice(&self.payload)
    }

    /// Format for logging: [I2I:TYPE] from — bytes
    pub fn to_header(&self) -> String {
        format!("[I2I:{}] {} — {} bytes", self.msg_type, self.from, self.payload.len())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn round_trip_message() {
        let msg = I2iMessage::new(
            I2iType::Task,
            "thor-1",
            serde_json::to_vec(&serde_json::json!({"job": "batch_solve"})).unwrap(),
        );
        let json = serde_json::to_string(&msg).unwrap();
        let parsed: I2iMessage = serde_json::from_str(&json).unwrap();
        assert_eq!(parsed.msg_type, I2iType::Task);
        assert_eq!(parsed.from, "thor-1");
    }

    #[test]
    fn header_format() {
        let msg = I2iMessage::new(I2iType::Blocker, "forgemaster", vec![1, 2, 3]);
        assert!(msg.to_header().contains("[I2I:BLOCKER]"));
    }
}

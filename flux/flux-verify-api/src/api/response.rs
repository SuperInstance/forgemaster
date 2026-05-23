use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct TraceEntry {
    pub opcode: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub value: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub result: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub expected: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub actual: Option<f64>,
    pub desc: String,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(untagged)]
pub enum CounterexampleValue {
    Number(f64),
    String(String),
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct VerifyResponse {
    pub status: String, // "PROVEN" | "DISPROVEN" | "UNKNOWN"
    pub confidence: f64,
    pub trace: Vec<TraceEntry>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub counterexample: Option<serde_json::Value>,
    pub proof_hash: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub plato_tile_id: Option<String>,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct StatusResponse {
    pub total_verifications: u64,
    pub proven: u64,
    pub disproven: u64,
    pub unknown: u64,
    pub avg_latency_ms: f64,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct HealthResponse {
    pub status: String,
    pub version: String,
}

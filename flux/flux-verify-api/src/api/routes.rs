use axum::{
    extract::State,
    http::StatusCode,
    response::Json,
    routing::{get, post},
    Router,
};
use std::sync::Arc;
use std::time::Instant;
use tokio::sync::Mutex;
use uuid::Uuid;

use crate::api::request::VerifyRequest;
use crate::api::response::{HealthResponse, StatusResponse, VerifyResponse};
use crate::compiler;
use crate::config::Config;
use crate::engine::vm::FluxVm;
use crate::provenance::merkle;
use crate::plato::client::PlatoClient;

#[derive(Debug)]
pub struct AppState {
    pub config: Config,
    pub total: u64,
    pub proven: u64,
    pub disproven: u64,
    pub unknown: u64,
    pub total_latency_ms: f64,
}

impl AppState {
    pub fn new(config: Config) -> Self {
        Self {
            config,
            total: 0,
            proven: 0,
            disproven: 0,
            unknown: 0,
            total_latency_ms: 0.0,
        }
    }
}

pub fn router() -> Router<Arc<Mutex<AppState>>> {
    Router::new()
        .route("/verify", post(verify))
        .route("/status", get(status))
        .route("/health", get(health))
}

async fn verify(
    State(state): State<Arc<Mutex<AppState>>>,
    Json(req): Json<VerifyRequest>,
) -> Result<(StatusCode, Json<VerifyResponse>), (StatusCode, Json<serde_json::Value>)> {
    let start = Instant::now();

    // Parse the claim into a constraint problem
    let problem = compiler::parse_claim(&req.claim, &req.domain)
        .map_err(|e| {
            (
                StatusCode::UNPROCESSABLE_ENTITY,
                Json(serde_json::json!({ "error": e })),
            )
        })?;

    // Compile to FLUX bytecodes
    let bytecodes = compiler::compile(&problem);

    // Execute on the VM
    let mut vm = FluxVm::new();
    let trace = vm.execute(&bytecodes);

    // Determine verdict from the trace
    let (verdict, confidence, counterexample) = vm.evaluate(&trace, &problem);

    // Merkle hash the trace
    let proof_hash = merkle::hash_trace(&trace);

    // Optionally submit to PLATO
    let plato_tile_id = {
        let state_guard = state.lock().await;
        if state_guard.config.plato_url.is_some() {
            let client = PlatoClient::new(
                state_guard.config.plato_url.clone().unwrap(),
                state_guard.config.plato_token.clone(),
            );
            drop(state_guard);
            let tile_id = format!("verification-{}", Uuid::new_v4().as_simple());
            let _ = client.submit(&proof_hash, &verdict, &req.claim).await;
            Some(tile_id)
        } else {
            None
        }
    };

    let response = VerifyResponse {
        status: verdict.clone(),
        confidence,
        trace,
        counterexample,
        proof_hash: format!("sha256:{}", proof_hash),
        plato_tile_id,
    };

    // Update stats
    let elapsed_ms = start.elapsed().as_secs_f64() * 1000.0;
    {
        let mut s = state.lock().await;
        s.total += 1;
        s.total_latency_ms += elapsed_ms;
        match verdict.as_str() {
            "PROVEN" => s.proven += 1,
            "DISPROVEN" => s.disproven += 1,
            _ => s.unknown += 1,
        }
    }

    let status_code = if verdict == "PROVEN" {
        StatusCode::OK
    } else {
        StatusCode::OK // Both proven and disproven are 200 — the status field tells you
    };

    Ok((status_code, Json(response)))
}

async fn status(
    State(state): State<Arc<Mutex<AppState>>>,
) -> Json<StatusResponse> {
    let s = state.lock().await;
    let avg = if s.total > 0 {
        s.total_latency_ms / s.total as f64
    } else {
        0.0
    };
    Json(StatusResponse {
        total_verifications: s.total,
        proven: s.proven,
        disproven: s.disproven,
        unknown: s.unknown,
        avg_latency_ms: avg,
    })
}

async fn health() -> Json<HealthResponse> {
    Json(HealthResponse {
        status: "ok".into(),
        version: "0.1.0".into(),
    })
}

use std::sync::Arc;
use std::time::Instant;
use axum::{
    Json, Router,
    extract::{State, WebSocketUpgrade, ws::{Message, WebSocket}},
    response::IntoResponse,
    routing::{get, post},
};
use serde::{Deserialize, Serialize};
use tokio::sync::RwLock;
use tower_http::cors::CorsLayer;
use crate::bytecode::Bytecode;
use crate::vm::{ExecutionLimits, Vm};

/// Shared server state.
#[derive(Clone)]
pub struct AppState {
    pub start_time: Instant,
    pub tiles_processed: Arc<RwLock<u64>>,
    pub constraint_violations: Arc<RwLock<u64>>,
    pub vm_limits: ExecutionLimits,
    pub node_id: String,
}

/// POST /execute request.
#[derive(Debug, Deserialize)]
pub struct ExecuteRequest {
    pub bytecode: Bytecode,
    #[serde(default)]
    pub inputs: Vec<f64>,
    #[serde(default)]
    pub limits: Option<ExecutionLimits>,
}

/// POST /validate request.
#[derive(Debug, Deserialize)]
pub struct ValidateRequest {
    pub values: Vec<f64>,
    pub min: f64,
    pub max: f64,
}

/// POST /validate response.
#[derive(Debug, Serialize)]
pub struct ValidateResponse {
    pub valid: Vec<bool>,
    pub all_valid: bool,
    pub violation_count: usize,
}

/// GET /status response.
#[derive(Debug, Serialize)]
pub struct StatusResponse {
    pub node_id: String,
    pub uptime_secs: f64,
    pub tiles_processed: u64,
    pub constraint_violations: u64,
    pub vm_limits: ExecutionLimits,
}

/// GET /health response.
#[derive(Debug, Serialize)]
pub struct HealthResponse {
    pub status: String,
    pub node_id: String,
}

/// Build the Axum router.
pub fn build_router(state: AppState) -> Router {
    Router::new()
        .route("/execute", post(execute_handler))
        .route("/validate", post(validate_handler))
        .route("/status", get(status_handler))
        .route("/health", get(health_handler))
        .route("/stream", get(ws_stream_handler))
        .layer(CorsLayer::permissive())
        .with_state(Arc::new(state))
}

type SharedState = Arc<AppState>;

async fn execute_handler(
    State(state): State<SharedState>,
    Json(req): Json<ExecuteRequest>,
) -> impl IntoResponse {
    let limits = req.limits.unwrap_or_else(|| state.vm_limits.clone());
    let mut vm = Vm::new(limits);
    vm.push_inputs(&req.inputs);

    let result = vm.execute(&req.bytecode).await;

    {
        let mut tp = state.tiles_processed.write().await;
        *tp += 1;
    }
    if result.violations > 0 {
        let mut cv = state.constraint_violations.write().await;
        *cv += result.violations;
    }

    Json(result)
}

async fn validate_handler(
    State(state): State<SharedState>,
    Json(req): Json<ValidateRequest>,
) -> impl IntoResponse {
    let valid: Vec<bool> = req.values.iter()
        .map(|&v| v >= req.min && v <= req.max)
        .collect();
    let violation_count = valid.iter().filter(|&&v| !v).count();

    if violation_count > 0 {
        let mut cv = state.constraint_violations.write().await;
        *cv += violation_count as u64;
    }
    {
        let mut tp = state.tiles_processed.write().await;
        *tp += 1;
    }

    Json(ValidateResponse {
        all_valid: violation_count == 0,
        valid,
        violation_count,
    })
}

async fn status_handler(
    State(state): State<SharedState>,
) -> impl IntoResponse {
    let tp = *state.tiles_processed.read().await;
    let cv = *state.constraint_violations.read().await;
    Json(StatusResponse {
        node_id: state.node_id.clone(),
        uptime_secs: state.start_time.elapsed().as_secs_f64(),
        tiles_processed: tp,
        constraint_violations: cv,
        vm_limits: state.vm_limits.clone(),
    })
}

async fn health_handler(
    State(state): State<SharedState>,
) -> impl IntoResponse {
    Json(HealthResponse {
        status: "ok".into(),
        node_id: state.node_id.clone(),
    })
}

async fn ws_stream_handler(
    ws: WebSocketUpgrade,
) -> impl IntoResponse {
    ws.on_upgrade(handle_socket)
}

async fn handle_socket(mut socket: WebSocket) {
    // Simple echo + heartbeat for live sensor stream.
    // In production, this would broadcast sensor pipeline results.
    while let Some(msg) = socket.recv().await {
        match msg {
            Ok(Message::Text(t)) => {
                if socket.send(Message::Text(t)).await.is_err() {
                    break;
                }
            }
            Ok(Message::Ping(data)) => {
                if socket.send(Message::Pong(data)).await.is_err() {
                    break;
                }
            }
            _ => break,
        }
    }
}
